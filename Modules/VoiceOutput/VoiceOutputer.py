import platform
import subprocess
import pyttsx3
import re
import threading

system = platform.system()
machine = platform.machine()

class VoiceOutputer:
    def __init__(self):
        self.engine = None

        if system == "Linux" and ("arm" in machine or "aarch64" in machine):
            # On Raspberry Pi — use espeak directly for real blocking behavior
            self.use_espeak_direct = True
        else:
            self.lock = threading.Lock()
            self.use_espeak_direct = False
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1)
            if system == "Darwin":
                self.engine.setProperty('voice', 'com.apple.voice.compact.zh-CN.Tingting')  # macOS default voice

    def speak(self, text):
        """Convert text to speech and block until done."""
        if self.use_espeak_direct:
            subprocess.run(['espeak-ng', '-s', '150', '-v', 'cmn-latn-pinyin', text], check=True)
        else:
            with self.lock:
                self.engine.say(text)
                self.engine.runAndWait()

    def stop(self):
        """Stop speech engine."""
        if not self.use_espeak_direct and self.engine:
            self.engine.stop()

    def getCurrentVolume(self):
        if system == "Darwin" or system == "Windows":
            return None
        try:
            output = subprocess.check_output(["amixer", "sget", "Master"]).decode()
            match = re.search(r'\[(\d+)%\]', output)
            if match:
                return int(match.group(1))
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None
    
    def setVolume(self, percent):
        if system == "Darwin" or system == "Windows":
            return
        try:
            subprocess.call(["amixer", "sset", "Master", f"{percent}%"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    def getActionInfo(self):
        if system == "Darwin":
            return ""
        current_volume = self.getCurrentVolume()
        if current_volume is not None:
            current_volume = str(current_volume) + "%"
        else:
            current_volume = "UNKNOWN"
        action_list_info = (
        "\n\n"
        "Action: ChangeVolume\n"
        "description: you can change the agent's sound volume because the agent device is also a music player.\n"
        "parameters:\n"
        "- percent: the percentage of the volume, must be integer, 0 to 100.\n"
        f"The current volume is: {current_volume}\n"
        + "\n\n"
    )
        return action_list_info

