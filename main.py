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
        agent_control.process_task()
        time.sleep(0.1)
    # except Exception as e:
    #     logger.error("Agent loop error: %s", e)
    #     agent_control.stop()



def handle_client(conn, addr):
    print(f"Connected by {addr}")
    with conn:
        buffer = ""
        while True:
            data = conn.recv(1024)
            if not data:
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
                        response = {"statuses": agent_control.get_status()}
                    else:
                        response = {"error": "Unknown action"}
                except Exception as e:
                    response = {"error": str(e)}
                response_str = json.dumps(response) + "\n"
                conn.sendall(response_str.encode())
    print(f"Disconnected {addr}")

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
