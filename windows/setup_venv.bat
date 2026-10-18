@echo off
setlocal
cd /d "%~dp0"

echo === JARVIS local setup ===
echo Recommended Python: 3.11 64-bit
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.11 -m venv .venv 2>nul
    if not exist ".venv\Scripts\python.exe" py -m venv .venv
) else (
    python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo Failed to create .venv. Install Python 3.11 64-bit and try again.
    pause
    exit /b 1
)

call .venv\Scripts\activate
python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt

echo.
echo === Python packages installed ===
where ollama >nul 2>nul
if %errorlevel%==0 (
    echo Ollama detected.
    echo Make sure this local model exists:
    echo   ollama pull qwen2.5:1.5b
    echo Optional screen vision:
    echo   ollama pull llava:7b
    echo Optional semantic document search:
    echo   ollama pull nomic-embed-text
) else (
    echo Ollama was not found in PATH.
    echo Install Ollama for Windows, then pull qwen2.5:1.5b.
)

echo.
echo Setup complete.
echo Interpreter: %CD%\.venv\Scripts\python.exe
pause
