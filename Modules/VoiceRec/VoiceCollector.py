import threading
import queue
import json
import sounddevice as sd
import tempfile
import os
import numpy as np

from sys import platform

# Optional import — only needed if using Vosk
try:
    from vosk import Model as VoskModel, KaldiRecognizer
except ImportError:
    VoskModel = KaldiRecognizer = None

# Whisper.cpp wrapper
from whispercpp import Whisper
import soundfile as sf


class VoiceCollector:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, mode="vosk", model_path="Modules/VoiceRec/models/vosk-model-small-cn-0.22", whisper_model_path="/Users/linick/Desktop/85Home/Modules/VoiceRec/models/ggml-tiny.en.bin", samplerate=16000):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.mode = mode
        self.samplerate = samplerate
        self._callback = None
        self._running = False
        self._thread = None
        self._stream = None
        self.q = queue.Queue()

        if self.mode == "vosk":
            if not KaldiRecognizer:
                raise RuntimeError("Vosk not installed")
            self.model = VoskModel(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.samplerate)
        elif self.mode == "whispercpp":
            self.whisper = Whisper.from_pretrained("tiny.en")
            self.audio_buffer = []
            self.buffer_duration_sec = 2  # Collect 3 seconds before transcribing
        else:
            raise ValueError("mode must be 'vosk' or 'whispercpp'")

        self._initialized = True

    def _audio_callback(self, indata, frames, time, status):
        if self.mode == "vosk":
            self.q.put(bytes(indata))
        elif self.mode == "whispercpp":
            # Convert to numpy array and store in buffer
            self.audio_buffer.append(indata.copy())

    def _monitor_loop(self):
        if self.mode == "vosk":
            while self._running:
                data = self.q.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                    if text and self._callback:
                        self._callback(text)

        elif self.mode == "whispercpp":
            chunk_size = int(self.samplerate * self.buffer_duration_sec)

            while self._running:
                if len(self.audio_buffer) * 1600 >= chunk_size:
                    all_data = np.concatenate(self.audio_buffer)
                    self.audio_buffer.clear()

                    # Save to temp wav file
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        wav_path = f.name
                        import soundfile as sf
                        sf.write(wav_path, all_data, self.samplerate, format='WAV')

                    try:
                        samples,_ = sf.read(wav_path, dtype='float32')
                        audio_data = samples.tolist()
                        text = self.whisper.transcribe(audio_data)
                        if text.strip() and "BLANK_AUDIO" not in text and self._callback:
                            self._callback(text.strip())
                    finally:
                        os.remove(wav_path)

    def Start(self):
        if self._running:
            return
        self._running = True

        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            blocksize=400,
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
