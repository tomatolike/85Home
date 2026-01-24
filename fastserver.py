from Core.utility import setup_logging, get_logger
import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import socket
import json
import threading

setup_logging("85server.log")
logger = get_logger("HomeServer")

AGENT_HOST = "127.0.0.1"
AGENT_PORT = 9001

# Persistent TCP connection
_tcp_socket = None
_tcp_lock = threading.Lock()
_tcp_buffer = ""
_response_ready = threading.Event()
_pending_response = None

def _connect_to_agent():
    """Establish persistent connection to agent"""
    global _tcp_socket, _tcp_buffer
    try:
        _tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        _tcp_socket.connect((AGENT_HOST, AGENT_PORT))
        _tcp_buffer = ""
        logger.info("Connected to agent control server")
        # Start background thread to receive data
        threading.Thread(target=_receive_loop, daemon=True).start()
    except Exception as e:
        logger.error(f"Failed to connect to agent: {e}")
        _tcp_socket = None

def _receive_loop():
    """Background thread to receive data from agent"""
    global _tcp_socket, _tcp_buffer, _pending_response, _response_ready
    while True:
        if _tcp_socket is None:
            time.sleep(0.1)
            continue
        try:
            data = _tcp_socket.recv(1024)
            if not data:
                logger.warning("Connection to agent closed, reconnecting...")
                if _tcp_socket:
                    try:
                        _tcp_socket.close()
                    except:
                        pass
                _tcp_socket = None
                time.sleep(1)
                _connect_to_agent()
                continue
            _tcp_buffer += data.decode()
            # Process complete messages
            while "\n" in _tcp_buffer:
                line, _tcp_buffer = _tcp_buffer.split("\n", 1)
                try:
                    response = json.loads(line)
                    _pending_response = response
                    _response_ready.set()
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse response: {line}")
        except Exception as e:
            logger.error(f"Error receiving from agent: {e}")
            if _tcp_socket:
                try:
                    _tcp_socket.close()
                except:
                    pass
            _tcp_socket = None
            time.sleep(1)
            _connect_to_agent()

def send_command(command: dict):
    """Send command using persistent connection"""
    global _tcp_socket, _pending_response, _response_ready
    
    with _tcp_lock:
        # Ensure connection exists
        if _tcp_socket is None:
            _connect_to_agent()
            if _tcp_socket is None:
                return {"error": "Failed to connect to agent"}
        
        # Clear previous response state
        _pending_response = None
        _response_ready.clear()
        
        try:
            # Send command
            _tcp_socket.sendall((json.dumps(command) + "\n").encode())
            
            # Wait for response (with timeout)
            if _response_ready.wait(timeout=5.0):
                response = _pending_response
                _pending_response = None
                return response if response else {"error": "Empty response"}
            else:
                return {"error": "Timeout waiting for response"}
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            _tcp_socket = None
            return {"error": str(e)}

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _connect_to_agent()
    yield
    # Shutdown
    global _tcp_socket
    if _tcp_socket:
        _tcp_socket.close()
        _tcp_socket = None

app = FastAPI(lifespan=lifespan)

@app.post("/task")
async def post_task(task: dict):
    command = {"action": "server_task", "data": task}
    response = send_command(command)
    return response

@app.get("/status")
async def get_status():
    command = {"action": "server_status"}
    response = send_command(command)
    return response

# Serve React frontend
import os

# Mount static files if build directory exists
if os.path.exists("frontend/build/static"):
    app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

@app.get("/")
async def serve_index():
    """Serve React frontend index.html"""
    if os.path.exists("frontend/build/index.html"):
        return FileResponse("frontend/build/index.html")
    return {"error": "Frontend not built. Run 'npm run build' in frontend directory"}

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve React frontend - catch all routes for client-side routing"""
    # Don't interfere with API routes
    if full_path.startswith("api/") or full_path == "task" or full_path == "status":
        return {"error": "Not found"}
    # Serve index.html for all other routes (React Router will handle routing)
    if os.path.exists("frontend/build/index.html"):
        return FileResponse("frontend/build/index.html")
    return {"error": "Frontend not built. Run 'npm run build' in frontend directory"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
