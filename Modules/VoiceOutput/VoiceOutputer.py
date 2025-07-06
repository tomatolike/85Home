import platform
import subprocess
import pyttsx3

system = platform.system()
machine = platform.machine()


class VoiceOutputer:
    def __init__(self):
        self.engine = None

        if system == "Linux" and ("arm" in machine or "aarch64" in machine):
            # On Raspberry Pi — use espeak directly for real blocking behavior
            self.use_espeak_direct = True
        else:
            self.use_espeak_direct = False
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1)
            if system == "Darwin":
                self.engine.setProperty('voice', 134)  # macOS default voice
            elif system == "Linux":
                print("setting voice to 14")
                self.engine.setProperty('voice', 14)  # May not be needed if voice names are different

    def speak(self, text):
        """Convert text to speech and block until done."""
        if self.use_espeak_direct:
            subprocess.run(['espeak-ng', '-s', '130', text], check=True)
        else:
            self.engine.say(text)
            self.engine.runAndWait()

    def stop(self):
        """Stop speech engine."""
        if not self.use_espeak_direct and self.engine:
            self.engine.stop()

