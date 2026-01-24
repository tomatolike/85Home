from Core.AgentControl import AgentControl
from Core.utility import setup_logging, get_logger
import time
import threading
import socket
import json

setup_logging()
logger = get_logger("Home")

agent_control = AgentControl()

def agent_loop():
    # try:
    logger.info("Agent is running...")
    agent_control.start()
    while True:
        try:
            agent_control.process_task()
            time.sleep(0.1)
        except Exception as e:
            logger.error("Agent loop error: %s", e)
    #     agent_control.stop()



def handle_client(conn, addr):
    """Handle persistent client connection - keep connection alive for multiple requests"""
    logger.info(f"Client connected from {addr}")
    try:
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        buffer = ""
        while True:
            try:
                conn.settimeout(60.0)  # Set timeout to detect dead connections
                data = conn.recv(1024)
                if not data:
                    logger.info(f"Client {addr} disconnected")
                    break
                buffer += data.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    response = {}
                    try:
                        request = json.loads(line)
                        
                        if request["action"] == "server_task":
                            agent_control.push_task(request["data"])
                            response = {"result": "Task received"}
                        elif request["action"] == "server_status":
                            try:
                                status = agent_control.get_status()
                                response = {"statuses": status}
                            except Exception as e:
                                logger.error(f"Error getting status: {e}")
                                response = {"error": f"Failed to get status: {str(e)}"}
                        else:
                            response = {"error": "Unknown action"}
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        response = {"error": f"Invalid JSON: {str(e)}"}
                    except Exception as e:
                        logger.error(f"Error handling request: {e}", exc_info=True)
                        response = {"error": str(e)}
                    try:
                        response_str = json.dumps(response, ensure_ascii=False) + "\n"
                        conn.sendall(response_str.encode('utf-8'))
                    except (TypeError, ValueError) as e:
                        logger.error(f"Error serializing response: {e}")
                        error_response = {"error": "Failed to serialize response"}
                        conn.sendall((json.dumps(error_response) + "\n").encode('utf-8'))
            except socket.timeout:
                # Connection still alive, just no data - continue
                continue
            except Exception as e:
                logger.error(f"Error handling client {addr}: {e}")
                break
    except Exception as e:
        logger.error(f"Connection error with {addr}: {e}")
    finally:
        try:
            conn.close()
        except:
            pass
        logger.info(f"Connection to {addr} closed")

def run_agent_control_server(host="127.0.0.1", port=9001):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"AgentControl server listening on {host}:{port}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


threading.Thread(target=run_agent_control_server, daemon=True).start()
agent_loop()
