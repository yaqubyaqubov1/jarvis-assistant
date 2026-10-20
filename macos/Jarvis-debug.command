#!/bin/zsh
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo "Missing virtual environment. Run: zsh setup_macos.command"
  exit 1
fi
source .venv/bin/activate
export PYTHONFAULTHANDLER=1
python -u main.py
status=$?
echo "JARVIS exited with code $status"
read '?Press Return to close Terminal: '
exit $status
