import threading
import wave
from pathlib import Path
import numpy as np
import sounddevice as sd
import pyttsx3
from config import TTS_ENGINE, PIPER_MODEL

_lock = threading.Lock()
_engine = None
_piper = None

def _sapi(text):
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", 180)
    _engine.say(str(text))
    _engine.runAndWait()

def _piper_speak(text):
    global _piper
    try:
        from piper.voice import PiperVoice
    except ImportError:
        return _sapi(text)
    if not PIPER_MODEL.exists():
        return _sapi(text)
    if _piper is None:
        _piper = PiperVoice.load(str(PIPER_MODEL))
    # Modern piper-tts can synthesize directly to a WAV stream.
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with wave.open(path, "wb") as wav_file:
            _piper.synthesize_wav(str(text), wav_file)
        with wave.open(path, "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            dtype = np.int16 if wav_file.getsampwidth() == 2 else np.int8
            audio = np.frombuffer(frames, dtype=dtype)
            if wav_file.getnchannels() > 1:
                audio = audio.reshape(-1, wav_file.getnchannels())
            sd.play(audio, wav_file.getframerate())
            sd.wait()
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

def speak(text):
    text = str(text).strip()
    if not text:
        return
    print(f"JARVIS: {text}")
    with _lock:
        if TTS_ENGINE.lower() == "piper":
            _piper_speak(text)
        else:
            _sapi(text)
