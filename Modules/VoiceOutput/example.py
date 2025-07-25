from VoiceOutputer import VoiceOutputer
import time

outputer = VoiceOutputer()
outputer.speak("Hello, this is a test of the voice output system.")
print("back")
print(outputer.getCurrentVolume())
outputer.setVolume(50)
time.sleep(5)
outputer.setVolume(100)
outputer.stop()
