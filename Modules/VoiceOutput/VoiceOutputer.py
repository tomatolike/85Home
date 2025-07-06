import pyttsx3
import platform

system = platform.system()
machine = platform.machine()


class VoiceOutputer:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 130)  # Set speech rate
        self.engine.setProperty('volume', 1)  # Set volume level (0.0 to 1.0)
        if system == "Darwin":
            pass
        elif system == "Linux":
            self.engine.setProperty('voice', 28)

    def speak(self, text):
        """Convert text to speech."""
        self.engine.say(text)
        self.engine.runAndWait()

    def stop(self):
        """Stop the speech engine."""
        self.engine.stop()
