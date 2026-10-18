@echo off

cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo JARVIS virtual environment was not found.
    echo Run setup_venv.bat first.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" main.py

exit