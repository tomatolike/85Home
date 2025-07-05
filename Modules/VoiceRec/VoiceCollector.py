import threading
import queue
import json
import sounddevice as sd
import webrtcvad
from vosk import Model, KaldiRecognizer


class VoiceCollector:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_path="/media/lovetomatoboy/RASP1/models/vosk-model-small-en-us-0.15", samplerate=16000):
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

        # VAD setup
        self.vad = webrtcvad.Vad(2)  # Aggressiveness: 0-3
        self.frame_duration_ms = 10
        self.frame_size_bytes = int(self.samplerate * self.frame_duration_ms / 1000) * 2  # 16-bit mono

        self._initialized = True

    def _audio_callback(self, indata, frames, time, status):
        self.q.put(bytes(indata))

    def _monitor_loop(self):
        buffer = b""
        while self._running:
            data = self.q.get()
            buffer += data

            while len(buffer) >= self.frame_size_bytes:
                frame = buffer[:self.frame_size_bytes]
                buffer = buffer[self.frame_size_bytes:]

                if self.vad.is_speech(frame, self.samplerate):
                    if self.recognizer.AcceptWaveform(frame):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "")
                        if text and self._callback:
                            self._callback(text)
                # else: skip silent frame

    def Start(self):
        if self._running:
            return  # Already running
        self._running = True

        self._stream = sd.RawInputStream(
            samplerate=self.samplerate,
            blocksize=self.samplerate,
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
