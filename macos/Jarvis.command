#!/bin/zsh
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo "Missing virtual environment. Run: zsh setup_macos.command"
  exit 1
fi
source .venv/bin/activate
exec python main.py
