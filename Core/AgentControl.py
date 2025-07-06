from Modules.VoiceRec.VoiceCollector import VoiceCollector
from Modules.DeviceControl.DeviceController import DeviceController
from Modules.AiContact.AiContactor import AiContactor
from Modules.VoiceOutput.VoiceOutputer import VoiceOutputer
from Core.utility import get_logger
import queue
import json

class AgentControl:
    _instance = None
    _agent_name = "eighty six"

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def get_voice_input(text):
        if AgentControl._agent_name not in text:
            return
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

    def re_generate_system_message(self):
        action_list_info = self.device_controller.getActionInfo()
        self.ai_contactor.generate_system_message(action_list_info)

    def process_response(self, action):
        try:
            self.logger.info(f"Action received: {action}")
            if action["action"] == "ControlDevice":
                aliases = action["action_params"]["alias"]
                ons = action["action_params"]["on"]
                self.device_controller.turnOnDevice(aliases, ons)
                self.re_generate_system_message()
            elif action["action"] == "MessageOnly":
                pass
            else:
                raise ValueError(f"Unknown action: {action['action']}")

            if action["message"] != "":
                self.voice_outputer.speak(action["message"])
        except Exception as e:
            self.logger.error(f"Error processing response: {e}")
            

    def process_task(self):
        if not self.task_queue.empty():
            task = self.task_queue.get()
            if task["type"] == "voice_input":
                self.stop_voice_collection()
                self.voice_outputer.speak("eighty six here")
                self.logger.info(f"User said: {task['text']}")
                response = self.ai_contactor.communicate(task["text"])
                self.process_response(response)
                self.start_voice_collection()

    def start_voice_collection(self):
        self.voice_collector.Start()

    def stop_voice_collection(self):
        self.voice_collector.Stop()

    def start(self):
        self.start_voice_collection()
    
    def stop(self):
        self.stop_voice_collection()
        self.voice_outputer.stop()