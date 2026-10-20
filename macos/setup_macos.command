#!/bin/zsh
# Run with: zsh setup_macos.command
set -e
cd -- "${0:A:h}"

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "Python 3.11 is required. Install it from https://www.python.org/downloads/macos/"
  echo "Then close Terminal, reopen it and run: zsh setup_macos.command"
  exit 1
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This setup script is for macOS only."
  exit 1
fi

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-macos.txt
python -m playwright install chromium
python -m pip check

if [[ ! -d models/vosk-model-small-en-us-0.15 ]]; then
  echo "WARNING: Missing models/vosk-model-small-en-us-0.15 (Vosk wake-word model)."
fi
if ! command -v ollama >/dev/null 2>&1; then
  echo "WARNING: Install Ollama from https://ollama.com/download/mac"
else
  echo "After starting Ollama, run: ollama pull qwen2.5:1.5b"
  echo "Optional screen vision: ollama pull llava:7b"
fi

echo "Setup complete. Run: zsh Jarvis.command"
echo "Grant Microphone, Accessibility and Screen Recording permissions in System Settings."
