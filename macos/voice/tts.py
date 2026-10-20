"""macOS voice playback. Native `say` works without Piper."""
import os
import subprocess
import tempfile
import threading
import wave
from pathlib import Path

from config import TTS_ENGINE, PIPER_MODEL

_lock = threading.Lock()
_piper = None


def _native_speak(text):
    result = subprocess.run(['say', '-r', '180', str(text)], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'macOS say failed')


def _piper_speak(text):
    global _piper
    if not Path(PIPER_MODEL).is_file():
        return _native_speak(text)
    try:
        from piper.voice import PiperVoice
        import numpy as np
        import sounddevice as sd
    except ImportError:
        return _native_speak(text)
    if _piper is None:
        try:
            _piper = PiperVoice.load(str(PIPER_MODEL))
        except Exception:
            return _native_speak(text)
    fd, path = tempfile.mkstemp(suffix='.wav')
    os.close(fd)
    try:
        with wave.open(path, 'wb') as output:
            _piper.synthesize_wav(str(text), output)
        with wave.open(path, 'rb') as audio_file:
            sample_width = audio_file.getsampwidth()
            if sample_width not in (1, 2):
                raise RuntimeError(f'Unsupported Piper sample width: {sample_width}')
            audio = np.frombuffer(audio_file.readframes(audio_file.getnframes()), dtype=np.int16 if sample_width == 2 else np.uint8)
            if audio_file.getnchannels() > 1:
                audio = audio.reshape(-1, audio_file.getnchannels())
            sd.play(audio, audio_file.getframerate())
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
    print(f'JARVIS: {text}')
    with _lock:
        if TTS_ENGINE.lower() == 'piper':
            _piper_speak(text)
        else:
            _native_speak(text)
