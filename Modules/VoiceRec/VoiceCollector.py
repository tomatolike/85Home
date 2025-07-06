import threading
import queue
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer


class VoiceCollector:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_path="Modules/VoiceRec/models/vosk-model-small-en-us-0.15", samplerate=16000):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.model = Model(model_path)
        self.samplerate = samplerate
        self.recognizer = KaldiRecognizer(self.model, self.samplerate)
        self.q = queue.Queue()
        self._callback = None
        self._running = False
        self._thread = None
        self._stream = None

        self._initialized = True

    def _audio_callback(self, indata, frames, time, status):
        self.q.put(bytes(indata))

    def _monitor_loop(self):
        while self._running:
            data = self.q.get()
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "")
                if text and self._callback:
                    self._callback(text)

    def Start(self):
        if self._running:
            return  # Already running
        self._running = True

        self._stream = sd.RawInputStream(
            samplerate=self.samplerate,
            blocksize=16000,
            dtype='int16',
            channels=1,
            callback=self._audio_callback
        )
        self._stream.start()

        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def Stop(self):
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join()
            self._thread = None
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def SetCallback(self, callback_func):
        self._callback = callback_func