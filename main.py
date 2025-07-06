from Core.AgentControl import AgentControl
from Core.utility import setup_logging, get_logger
import time

if __name__ == "__main__":
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    agent_control = AgentControl()

    try:
        logger.info("Agent is running... Press Ctrl+C to stop.")
        agent_control.start()
        while True:
            agent_control.process_task()
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Stopping agent...")
        agent_control.stop()