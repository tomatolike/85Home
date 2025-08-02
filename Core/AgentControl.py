from Modules.VoiceRec.VoiceCollector import VoiceCollector
from Modules.DeviceControl.DeviceController import DeviceController
from Modules.AiContact.AiContactor import AiContactor
from Modules.VoiceOutput.VoiceOutputer import VoiceOutputer
from Core.utility import get_logger
import queue
import json
import time

class AgentControl:
    _instance = None
    _agent_name = "把握"

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def is_calling_agent(text):
        if AgentControl._agent_name in text:
            return True
        text = text.replace(" ", "")
        if AgentControl._agent_name in text:
            return True
        return False

    @staticmethod
    def get_voice_input(text):
        AgentControl._instance.logger.info(f"Voice input received: {text}")
        if not AgentControl._instance.wait_for_user_instruction:
            if not AgentControl.is_calling_agent(text):
                AgentControl._instance.logger.info(f"User said: {text} but not for me")
                return
            else:
                task = {
                    "type": "user_call_name",
                    "text": text
                }
                AgentControl._instance.push_task(task)
        else:
            task = {
                "type": "voice_input",
                "text": text
            }
            AgentControl._instance.push_task(task)

    def push_task(self, task):
        self.task_queue.put(task)

    def __init__(self):
        self.logger = get_logger(__name__)
        self.voice_collector = VoiceCollector()
        self.voice_collector.SetCallback(AgentControl.get_voice_input)
        self.task_queue = queue.Queue()
        self.device_controller = DeviceController()
        self.device_controller.updateDevices()
        self.ai_contactor = AiContactor()
        self.voice_outputer = VoiceOutputer()
        self.re_generate_system_message()
        self.wait_for_user_instruction = False
        self.last_time_update_devices = time.time()

    def re_generate_system_message(self):
        action_list_info = self.device_controller.getActionInfo()
        action_list_info += self.voice_outputer.getActionInfo()
        self.ai_contactor.generate_system_message(action_list_info)

    def process_response(self, action):
        try:
            self.logger.info(f"Action received: {action}")
            if action["action"] == "ControlDevice":
                aliases = action["action_params"]["alias"]
                statuses = action["action_params"]["status"]
                if action["message"] != "":
                    self.voice_outputer.speak(action["message"])
                self.device_controller.changeDeviceStatus(aliases, statuses)
                self.re_generate_system_message()
            elif action["action"] == "MessageOnly":
                if action["message"] != "":
                    self.voice_outputer.speak(action["message"])
                else:
                    if action["action"] == "MessageOnly":
                        self.voice_outputer.speak("我不明白")
                if action["action_params"]["isQuestion"]:
                    time.sleep(0.2)
                    self.voice_outputer.speak("请回答，哔哔：")
                    self.wait_for_user_instruction = True
            elif action["action"] == "ChangeVolume":
                if action["message"] != "":
                    self.voice_outputer.speak(action["message"])
                if action["action_params"]["percent"] < 0 or action["action_params"]["percent"] > 100:
                    task = {
                        "type": "system_message",
                        "text": f"Invalid volume number: {action['action_params']['percent']}. Must be integer between 0 and 100"
                    }
                    self.push_task(task)
                else:
                    self.voice_outputer.setVolume(action["action_params"]["percent"])
            else:
                raise ValueError(f"Unknown action: {action['action']}")

        except Exception as e:
            self.logger.error(f"Error processing response: {e}")
            

    def process_task(self):
        if not self.task_queue.empty():
            task = self.task_queue.get()
            self.logger.info(f"Processing task: {task}")
            if task["type"] == "user_call_name":
                self.stop_voice_collection()
                self.wait_for_user_instruction = True
                self.voice_outputer.speak("我在")
                self.start_voice_collection()
            elif task["type"] == "voice_input":
                self.wait_for_user_instruction = False
                self.stop_voice_collection()
                self.logger.info(f"User said: {task['text']}")
                response = self.ai_contactor.communicate(task["text"])
                self.process_response(response)
                self.start_voice_collection()
            elif task["type"] == "system_message":
                self.wait_for_user_instruction = False
                self.stop_voice_collection()
                self.logger.info(f"System Message: {task['text']}")
                response = self.ai_contactor.communicate(task["text"], from_type=3)
                self.process_response(response)
                self.start_voice_collection()

        now = time.time()
        if now - self.last_time_update_devices > 300:
            self.device_controller.updateDevices()
            self.last_time_update_devices = now
    

    def start_voice_collection(self):
        self.logger.info("Starting voice collection...")
        self.voice_collector.Start()

    def stop_voice_collection(self):
        self.logger.info("Stopping voice collection...")
        self.voice_collector.Stop()

    def start(self):
        self.start_voice_collection()
    
    def stop(self):
        self.stop_voice_collection()
        self.voice_outputer.stop()
