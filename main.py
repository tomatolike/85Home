from Core.AgentControl import AgentControl
from Core.utility import setup_logging, get_logger
import time
from fastapi import FastAPI
import threading

app = FastAPI()
setup_logging()
logger = get_logger("HomeServer")
agent_control = AgentControl()

def agent_loop():
    try:
        logger.info("Agent is running...")
        agent_control.start()
        while True:
            agent_control.process_task()
            time.sleep(0.1)
    except Exception as e:
        logger.info("Agent loop error:", e)
        agent_control.stop()

threading.Thread(target=agent_loop, daemon=True).start()

@app.post("/task")
async def post_task(task: dict):
    agent_control.push_task(task)  # Implement this method in AgentControl
    return {"result": "Task received"}

@app.get("/status")
async def get_status():
    return {"statuses": agent_control.get_status()}  # Implement this method