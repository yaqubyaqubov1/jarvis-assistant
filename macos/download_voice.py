"""Optional: download the publicly hosted Piper Ryan high voice model.

This is NOT required for default macOS `say` speech.
"""
from pathlib import Path
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
DESTINATION = ROOT / 'voices'
BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/'
FILES = {'en_US-ryan-high.onnx': 30_000_000,
         'en_US-ryan-high.onnx.json': 100}


def download(name, min_bytes):
    DESTINATION.mkdir(parents=True, exist_ok=True)
    target = DESTINATION / name
    if target.exists() and target.stat().st_size >= min_bytes:
        print('Already present:', target)
        return
    temporary = target.with_name(target.name + '.partial')
    try:
        request = urllib.request.Request(BASE + name, headers={'User-Agent': 'JARVIS-setup/1.0'})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open('wb') as output:
            import shutil
            shutil.copyfileobj(response, output)
        if temporary.stat().st_size < min_bytes:
            raise RuntimeError(f'Download too small for {name}')
        if name.endswith('.json'):
            json.loads(temporary.read_text(encoding='utf-8'))
        temporary.replace(target)
        print('Downloaded:', target)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    for filename, minimum in FILES.items():
        download(filename, minimum)
    print("To enable Piper: pip install piper-tts, then set TTS_ENGINE = 'piper' in config.py")
