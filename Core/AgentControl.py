from Modules.VoiceRec.VoiceCollector import VoiceCollector
import queue

class AgentControl:
    _instance = None

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def get_voice_input(text):
        task = {
            "type": "voice_input",
            "text": text
        }
        AgentControl._instance.push_task(task)

    def push_task(self, task):
        self.task_queue.put(task)

    def __init__(self):
        self.voice_collector = VoiceCollector()
        self.voice_collector.SetCallback(AgentControl.get_voice_input)
        self.task_queue = queue.Queue()

    def start(self):
        self.voice_collector.Start()

    def stop(self):
        self.voice_collector.Stop()
