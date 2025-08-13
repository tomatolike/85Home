from VoiceOutputer import VoiceOutputer
import time

outputer = VoiceOutputer()
outputer.speak("你好，这是一个测试！")
print("back")
print(outputer.getCurrentVolume())
outputer.setVolume(50)
time.sleep(5)
outputer.setVolume(100)
outputer.stop()
