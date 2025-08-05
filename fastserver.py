from Core.utility import setup_logging, get_logger
import time
from fastapi import FastAPI
import socket
import json

app = FastAPI()
setup_logging("85server.log")
logger = get_logger("HomeServer")

AGENT_HOST = "127.0.0.1"
AGENT_PORT = 9001

def send_command(command: dict):
    # Connect, send command, get response
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((AGENT_HOST, AGENT_PORT))
        s.sendall((json.dumps(command) + "\n").encode())

        buffer = ""
        while True:
            data = s.recv(1024)
            if not data:
                break
            buffer += data.decode()
            if "\n" in buffer:
                line, _ = buffer.split("\n", 1)
                return json.loads(line)

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
