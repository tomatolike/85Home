from Core.AgentControl import AgentControl
from Core.utility import setup_logging, get_logger
import time
from fastapi import FastAPI
import threading
import asyncio
app = FastAPI()
setup_logging()
logger = get_logger("HomeServer")

agent_control = None

def agent_loop():
    global agent_control
    agent_control = AgentControl()
    try:
        logger.info("Agent is running...")
        agent_control.start()
        while True:
            agent_control.process_task()
            time.sleep(0.1)
    except Exception as e:
        logger.error("Agent loop error: %s", e)
        agent_control.stop()

def after_start():
    threading.Thread(target=agent_loop, daemon=True).start()

@app.on_event("startup")
async def startup_event():
    asyncio.get_event_loop().call_soon(after_start)

@app.post("/task")
async def post_task(task: dict):
    agent_control.push_task(task)
    return {"result": "Task received"}

@app.get("/status")
async def get_status():
    return {"statuses": agent_control.get_status()}
