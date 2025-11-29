import json
import os
from pathlib import Path
from datetime import datetime
from Core.utility import get_logger

logger = get_logger(__name__)

class Timer:
    def __init__(self, timestamp, actions):
        self.timestamp = timestamp
        self.actions = actions

class SetTimer:

    def __init__(self):
        self.timers = [] # list of Timer objects sorted by timestamp
        self.timer_dir = Path("timers")
        self.timer_dir.mkdir(exist_ok=True)
        
        # Read files from local folder
        # Each scheduled timer is a local file, named by "timer_<timestamp>.json"
        # Load timers from files and put them into a queue
        self._load_timers_from_files()

    def _load_timers_from_files(self):
        """Load all timer files from the timer directory and add them to the queue"""
        try:
            for file_path in self.timer_dir.glob("timer_*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        timer = Timer(data['timestamp'], data['actions'])
                        self.timers.append(timer)
                except Exception as e:
                    logger.error(f"Error loading timer file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error reading timer directory: {e}")
        self.timers.sort(key=lambda t: t.timestamp)

    def add_timer(self, timestamp, actions):
        # Create a new timer object, put it into the queue and save it to a local file
        timestamp = int(timestamp + datetime.now().timestamp())
        timer = Timer(timestamp, actions)
        self.timers.append(timer)
        self.timers.sort(key=lambda t: t.timestamp)
        
        # Save to local file
        file_path = self.timer_dir / f"timer_{timestamp}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump({'timestamp': timestamp, 'actions': actions}, f, indent=2)
            logger.info(f"Timer added and saved: {file_path}")
        except Exception as e:
            logger.error(f"Error saving timer file {file_path}: {e}")

    def execute_timers(self):
        # Go through the queue, return all timers that are due to be executed
        # Also, clean the local files of these returned timers and remove them from the queue
        current_time = datetime.now().timestamp()
        due_timers = []
        remaining_timers = []
        
        for timer in self.timers:
            if timer.timestamp <= current_time:
                due_timers.append(timer)
                # Clean the local file
                file_path = self.timer_dir / f"timer_{timer.timestamp}.json"
                try:
                    if file_path.exists():
                        file_path.unlink()
                    logger.info(f"Timer file deleted: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting timer file {file_path}: {e}")
            else:
                remaining_timers.append(timer)
        
        # Update the queue with remaining timers
        self.timers = remaining_timers
        
        return due_timers
    
    def getActionInfo(self):
        action_list_info = (
        "\n\n"
        "Action: SetTimer\n"
        "description: you can set a timer to do some actions in the future\n"
        "parameters:\n"
        "- timestamp: the timestamp that the actions should be execute, precise in seconds, for example it should 30 if we want to execute acitons 30 seconds later\n"
        "- actions: a list of actions, please note each action should also be a valid action that home agent can execute (contains message, action, action_params), and can't be SetTimer (no nested SetTimer)\n"
        + "\n\n"
    )
        return action_list_info