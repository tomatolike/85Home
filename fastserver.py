from Core.utility import setup_logging, get_logger
import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import socket
import json
import threading
import os
import glob
import random
import platform

setup_logging("85server.log")
logger = get_logger("HomeServer")

AGENT_HOST = "127.0.0.1"
AGENT_PORT = 9001

# TCP keepalive tuning: detect dead connections within ~45s instead of ~2h
_KEEPALIVE_IDLE = 15    # seconds idle before first probe
_KEEPALIVE_INTERVAL = 5 # seconds between probes
_KEEPALIVE_COUNT = 6    # probes before declaring dead

# Persistent TCP connection
_tcp_socket = None
_tcp_lock = threading.Lock()
_tcp_buffer = ""
_response_ready = threading.Event()
_pending_response = None
# Track the receive thread so we never start more than one at a time.
_receive_thread = None
_receive_thread_lock = threading.Lock()
# Heartbeat thread for proactive reconnection
_heartbeat_thread = None


def _configure_keepalive(sock):
    """Set aggressive TCP keepalive on the socket to detect dead connections fast."""
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if platform.system() == "Linux":
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, _KEEPALIVE_IDLE)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, _KEEPALIVE_INTERVAL)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, _KEEPALIVE_COUNT)
    elif platform.system() == "Darwin":
        # macOS: TCP_KEEPALIVE controls the idle time
        TCP_KEEPALIVE = 0x10
        sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, _KEEPALIVE_IDLE)


def _close_socket(sock):
    """Safely close a socket, ignoring errors."""
    if sock is None:
        return
    try:
        sock.close()
    except Exception:
        pass


def _connect_to_agent():
    """Establish a persistent connection to the agent. Returns True on success.

    Caller should already hold _tcp_lock (or be running at startup before any
    requests can race with it). Only starts a receive thread if one isn't
    already alive.
    """
    global _tcp_socket, _tcp_buffer, _receive_thread
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _configure_keepalive(sock)
        sock.settimeout(5.0)  # connect timeout
        sock.connect((AGENT_HOST, AGENT_PORT))
        sock.settimeout(None)  # back to blocking for recv
        _tcp_socket = sock
        _tcp_buffer = ""
        logger.info("Connected to agent control server")
        # Start the receive loop only if there isn't already a live one.
        with _receive_thread_lock:
            if _receive_thread is None or not _receive_thread.is_alive():
                _receive_thread = threading.Thread(
                    target=_receive_loop, daemon=True, name="agent-recv"
                )
                _receive_thread.start()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to agent: {e}")
        _tcp_socket = None
        return False


def _receive_loop():
    """Background thread that drains the agent socket.

    Exits cleanly when the socket closes or errors. It does NOT attempt to
    reconnect — the next send_command() will notice _tcp_socket is None and
    trigger a fresh _connect_to_agent() under the lock, which will spawn a
    new receive thread. This guarantees at most one receive thread is alive
    at any time.
    """
    global _tcp_socket, _tcp_buffer, _pending_response, _response_ready
    logger.info("Receive loop started")
    try:
        while True:
            sock = _tcp_socket
            if sock is None:
                # Someone else (send_command) has invalidated the socket.
                # Exit; the next reconnect will start a fresh receive loop.
                logger.info("Receive loop exiting: socket is None")
                return
            try:
                data = sock.recv(1024)
            except Exception as e:
                logger.error(f"Error receiving from agent: {e}")
                try:
                    sock.close()
                except Exception:
                    pass
                if _tcp_socket is sock:
                    _tcp_socket = None
                return
            if not data:
                logger.warning("Connection to agent closed")
                try:
                    sock.close()
                except Exception:
                    pass
                if _tcp_socket is sock:
                    _tcp_socket = None
                return
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
    finally:
        logger.info("Receive loop exited")

def send_command(command: dict, timeout: float = 5.0):
    """Send command using persistent connection. Auto-reconnects on failure."""
    global _tcp_socket, _pending_response, _response_ready

    max_retries = 2
    for attempt in range(max_retries):
        with _tcp_lock:
            # Ensure connection exists
            if _tcp_socket is None:
                _connect_to_agent()
                if _tcp_socket is None:
                    if attempt < max_retries - 1:
                        continue
                    return {"error": "Failed to connect to agent"}

            # Clear previous response state
            _pending_response = None
            _response_ready.clear()

            try:
                # Send command
                _tcp_socket.sendall((json.dumps(command) + "\n").encode())
            except Exception as e:
                logger.error(f"Error sending command (attempt {attempt+1}): {e}")
                _close_socket(_tcp_socket)
                _tcp_socket = None
                if attempt < max_retries - 1:
                    continue
                return {"error": str(e)}

        # Wait for response OUTSIDE the lock so receive_loop can set it
        if _response_ready.wait(timeout=timeout):
            response = _pending_response
            _pending_response = None
            return response if response else {"error": "Empty response"}
        else:
            # Timeout — connection is likely dead. Tear it down so next call reconnects.
            logger.warning(f"Timeout waiting for agent response (attempt {attempt+1})")
            with _tcp_lock:
                _close_socket(_tcp_socket)
                _tcp_socket = None
            if attempt < max_retries - 1:
                continue
            return {"error": "Timeout waiting for response"}

    return {"error": "Failed after retries"}

def _heartbeat_loop():
    """Background thread that periodically pings the agent.

    If the connection is dead, it proactively reconnects so that the next
    user request doesn't have to wait for a timeout + reconnect cycle.
    Runs every 30 seconds.
    """
    global _tcp_socket
    logger.info("Heartbeat loop started")
    while True:
        time.sleep(30)
        try:
            with _tcp_lock:
                if _tcp_socket is None:
                    logger.info("Heartbeat: socket is None, attempting reconnect")
                    _connect_to_agent()
                    continue
                # Send a lightweight ping to verify the connection is alive
                try:
                    # Bare newline = ping; main.py skips blank lines silently.
                    _tcp_socket.sendall(b"\n")
                except Exception as e:
                    logger.warning(f"Heartbeat: send failed ({e}), reconnecting")
                    _close_socket(_tcp_socket)
                    _tcp_socket = None
                    _connect_to_agent()
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _heartbeat_thread
    # Startup
    _connect_to_agent()
    _heartbeat_thread = threading.Thread(
        target=_heartbeat_loop, daemon=True, name="agent-heartbeat"
    )
    _heartbeat_thread.start()
    yield
    # Shutdown
    global _tcp_socket
    if _tcp_socket:
        _close_socket(_tcp_socket)
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

# Screensaver endpoints
def get_screensaver_config():
    """Get screensaver folder path from config.json"""
    try:
        with open("config.json", encoding="utf-8") as f:
            config = json.load(f)
            print("get screen sever config:", config)
            image_path=config.get("Screensaver", {}).get("ImageFolder", "screensaver_images")
            print("image path:", image_path)
            return image_path
    except Exception as e:
        print("get screen saver timeout exception", e)
        return "screensaver_images"

def get_screensaver_timeout():
    """Get screensaver timeout in minutes from config.json"""
    try:
        with open("config.json", encoding="utf-8") as f:
            config = json.load(f)
            print("get screen sever timeout:", config)
            timeout = config.get("Screensaver", {}).get("TimeoutMinutes", 5)
            print("timeout:",timeout)
            return timeout
    except Exception as e:
        print("get screen saver timeout exception", e)
        return 5

@app.get("/api/screensaver/config")
async def get_screensaver_config_api():
    """Get screensaver configuration"""
    return JSONResponse({
        "timeoutMinutes": get_screensaver_timeout(),
        "imageFolder": get_screensaver_config()
    })

def _get_all_images():
    """Get all available screensaver images from folder"""
    folder = get_screensaver_config()
    if not os.path.exists(folder):
        return []
    
    # Supported image formats
    extensions = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp"]
    images = []
    for ext in extensions:
        images.extend(glob.glob(os.path.join(folder, ext)))
        images.extend(glob.glob(os.path.join(folder, ext.upper())))
    
    return images

@app.get("/api/screensaver/random-image")
async def get_random_screensaver_image():
    """Get a random screensaver image URL"""
    images = _get_all_images()
    if not images:
        return JSONResponse({"error": "No images found", "imageUrl": None})
    
    # Pick a random image
    random_image = random.choice(images)
    folder = get_screensaver_config()
    image_name = os.path.relpath(random_image, folder)
    image_url = f"/api/screensaver/image/{image_name}"
    
    return JSONResponse({"imageUrl": image_url})

@app.get("/api/screensaver/image/{image_name:path}")
async def get_screensaver_image(image_name: str):
    """Serve a screensaver image"""
    folder = get_screensaver_config()
    image_path = os.path.join(folder, image_name)
    
    # Security: prevent path traversal
    if not os.path.abspath(image_path).startswith(os.path.abspath(folder)):
        return JSONResponse({"error": "Invalid path"}, status_code=400)
    
    if os.path.exists(image_path) and os.path.isfile(image_path):
        return FileResponse(image_path)
    return JSONResponse({"error": "Image not found"}, status_code=404)

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
        return JSONResponse({"error": "Not found"}, status_code=404)
    # Serve index.html for all other routes (React Router will handle routing)
    if os.path.exists("frontend/build/index.html"):
        return FileResponse("frontend/build/index.html")
    return JSONResponse({"error": "Frontend not built. Run 'npm run build' in frontend directory"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
