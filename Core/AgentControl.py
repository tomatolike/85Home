from Modules.VoiceRec.VoiceCollector import VoiceCollector
from Modules.DeviceControl.DeviceController import DeviceController
from Modules.AiContact.AiContactor import AiContactor
from Modules.VoiceOutput.VoiceOutputer import VoiceOutputer
from Modules.RobotServer.RobotTCPServer import RobotTCPServer
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
        if AgentControl._agent_name == text:
            return True
        text = text.replace(" ", "")
        if AgentControl._agent_name == text:
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

    @staticmethod
    def get_robot_status(status):
        task = {
            "type": "robot_status",
            "status": status
        }
        AgentControl._instance.push_task(task)

    def push_task(self, task):
        self.task_queue.put(task)

    def __init__(self):
        configs = {}
        with open("config.json") as f:
            configs = json.load(f)
        AgentControl._agent_name = configs['AgentName']
        self.logger = get_logger(__name__)
        self.voice_collector = VoiceCollector(mode="vosk",model_path=configs["Vosk"]["ModelPath"])
        self.voice_collector.SetCallback(AgentControl.get_voice_input)
        self.task_queue = queue.Queue()
        self.device_controller = DeviceController(switch_bot_creds=configs["SwitchBot"])
        self.device_controller.updateDevices()
        self.ai_contactor = AiContactor(mode="DEEPSEEK", key=configs["DeepSeek"]["Key"])
        self.voice_outputer = VoiceOutputer()
        self.wait_for_user_instruction = False
        self.last_time_update_devices = time.time()
        self.robot_server = RobotTCPServer(host='0.0.0.0', port=9000, callback=AgentControl.get_robot_status)
        self.robot_server.start()
        self.robot_status = {}

    def re_generate_system_message(self):
        action_list_info = self.device_controller.getActionInfo()
        action_list_info += self.voice_outputer.getActionInfo()
        self.ai_contactor.generate_system_message(action_list_info)

    def process_response(self, action, no_sound=False):
        try:
            self.logger.info(f"Action received: {action}")
            if action["action"] == "ControlDevice":
                aliases = action["action_params"]["alias"]
                statuses = action["action_params"]["status"]
                if action["message"] != "" and not no_sound:
                    self.voice_outputer.speak(action["message"])
                self.device_controller.changeDeviceStatus(aliases, statuses)
            elif action["action"] == "MessageOnly":
                if action["message"] != "" and not no_sound:
                    self.voice_outputer.speak(action["message"])
                else:
                    if action["action"] == "MessageOnly" and not no_sound:
                        self.voice_outputer.speak("我不明白")
                if action["action_params"]["isQuestion"]:
                    time.sleep(0.2)
                    if not no_sound:
                        self.voice_outputer.speak("请回答，哔哔：")
                        self.wait_for_user_instruction = True
            elif action["action"] == "ChangeVolume":
                if action["message"] != "" and not no_sound:
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
            
    def input_local_filter(self, text):
        success, action = self.device_controller.local_filter(text)
        if success:
            return success, action
        return False, {}

    def process_task(self):
        if not self.task_queue.empty():
            task = self.task_queue.get()
            if task["type"] != "robot_status":
                self.logger.info(f"Processing task: {task}")
            if task["type"] == "user_call_name":
                self.stop_voice_collection()
                self.wait_for_user_instruction = True
                self.voice_outputer.speak("我在")
                self.start_voice_collection()
            elif task["type"] == "voice_input" or task['type'] == "chat_message":
                self.wait_for_user_instruction = False
                self.stop_voice_collection()
                self.logger.info(f"User said: {task['text']}")
                self.re_generate_system_message()
                success, action = self.input_local_filter(task['text'])
                if success:
                    self.ai_contactor.add_message_history(task['text'])
                    self.ai_contactor.add_message_history(json.dumps(action), role="assistant")
                    self.process_response(action, task['type'] == "chat_message")
                else:
                    response = self.ai_contactor.communicate(task["text"])
                    self.process_response(response, task['type'] == "chat_message")
                self.start_voice_collection()
            elif task["type"] == "system_message":
                self.wait_for_user_instruction = False
                self.stop_voice_collection()
                self.logger.info(f"System Message: {task['text']}")
                self.re_generate_system_message()
                response = self.ai_contactor.communicate(task["text"], from_type=3)
                self.process_response(response)
                self.start_voice_collection()
            elif task["type"] == "robot_status":
                #self.logger.info(f"Robot status received: {task['status']}")
                self.robot_status = task["status"]
            elif task['type'] == "robot_move":
                self.robot_server.send_command("move", task['command'])
            elif task['type'] == "robot_car":
                self.robot_server.send_command("car", task['command'])
            elif task['type'] == "client_device":
                self.device_controller.changeDeviceStatus([task['target']], [task['targetStatus']])
        now = time.time()
        if now - self.last_time_update_devices > 300:
            self.device_controller.updateDevices()
            self.last_time_update_devices = now

    def get_status(self):
        status = {
            "messages": self.ai_contactor.get_message_list(),
            "devices": self.device_controller.getDevicesInfo(),
            "robot": {
                "connected": self.robot_server.is_connected,
                "status": self.robot_status
            }
        }
        return status

    def start_voice_collection(self):
        self.logger.info("Starting voice collection...")
        self.voice_collector.Start()

    def stop_voice_collection(self):
        self.logger.info("Stopping voice collection...")
        self.voice_collector.Stop()

    def start(self):
        self.start_voice_collection()
        self.voice_outputer.speak("已启动")
    
    def stop(self):
        self.stop_voice_collection()
        self.voice_outputer.stop()
