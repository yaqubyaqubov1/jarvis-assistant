# J.A.R.V.I.S. — Local Windows Desktop Agent

This build is designed to run locally. It does not require a cloud AI API key.

## Core behavior
- JARVIS remains asleep until the local Vosk wake detector hears **"Jarvis"**.
- Audio spoken before activation is discarded and is not sent to Whisper.
- By default, every new command requires the name **Jarvis** again.
- Set `ENABLE_FOLLOWUP_SESSION = True` in `config.py` to allow natural follow-up commands for 25 seconds.
- Faster-Whisper transcribes commands locally.
- Ollama + Qwen runs planning/conversation locally.
- Destructive or system-level actions go through the permission layer.

## Included features
- Local conversation and general knowledge through Ollama
- Fast direct commands for common actions
- Multi-step plans with tool chaining
- Permission checks and confirmations
- Basic post-action verification
- Undo for reversible create/copy/move/rename actions
- Notepad++ preference for "open notepad"
- App discovery/open/close and window inspection
- Mouse, keyboard, hotkeys, screenshots
- Optional local screen vision through Ollama `llava:7b`, including target location/clicking
- Browser navigation and optional web search
- File/folder creation, copy, move, rename, Recycle Bin deletion, ZIP/unZIP
- TXT/Markdown/code/CSV/JSON/PDF/DOCX reading
- Local keyword document search, optional semantic embedding search, and document Q&A
- Clipboard read/write
- System diagnostics, media/volume, brightness, Wi-Fi, lock/power controls
- SQLite memories, preferences, aliases and task history
- Timers, reminders, recurring reminders, snooze and cancel
- Windows desktop notifications
- Work/study/gaming/privacy modes and custom mode support
- Optional JARVIS HUD states: sleeping/listening/thinking/executing/verifying/done
- Local SAPI voice by default; optional included Piper Ryan voice
- Drop-in Python custom skills under `skills/custom/`

## Setup
1. Install **Python 3.11 64-bit**.
2. Install **Ollama for Windows**.
3. Open a terminal and run:
   `ollama pull qwen2.5:1.5b`
4. Optional local screen understanding:
   `ollama pull llava:7b`
5. Optional semantic document search:
   `ollama pull nomic-embed-text`
6. Run `setup_venv.bat`.
6. Start Ollama.
7. Run `Jarvis.bat`.

No API key is needed.

The first Faster-Whisper model download requires internet once unless the model is already cached. After models are installed, ordinary voice, AI, memory, computer-control and document tasks can work offline. Explicit web searches naturally require internet.

## Test order
1. `Jarvis` → `hello`
2. `Jarvis` → `open Notepad++`
3. `Jarvis` → `what time is it`
4. `Jarvis` → `remind me in two minutes to drink water`
5. `Jarvis` → `create a folder called AI Projects on desktop`
6. `Jarvis` → `what is recursion`
7. `Jarvis` → `take a screenshot`
8. Optional vision: `Jarvis` → `describe my screen`

## Voice accuracy
Default Whisper model is `base.en`. In `config.py`:
- `small.en`: more accurate, slower
- `base.en`: balanced
- `tiny.en`: faster, less accurate

If the wrong microphone is used, run:
`python test_microphone.py`
Then set `MIC_DEVICE` in `config.py` to the desired device index.

## Safety
The local LLM never gets unrestricted shell access. It can only request registered tools.
- Moves, renames, deletion, app closing, Wi-Fi and power controls require confirmation.
- Delete moves files to the Windows Recycle Bin.
- File tools are restricted to the current Windows user profile by default.
- `pyautogui.FAILSAFE` is enabled: moving the mouse to the top-left corner aborts PyAutoGUI actions.

## Notes
- Screen vision is optional and needs the local `llava:7b` Ollama model.
- Internet/search functions are optional; core JARVIS behavior is local.
- JARVIS must be running for voice activation and its internal reminder scheduler.
- Windows UI automation is inherently less reliable than direct app APIs; direct tools are preferred.

## Optional extras
- Run `pip install -r requirements_optional.txt` if you want the included Piper voice instead of Windows SAPI.
- Run `install_startup.bat` if you want JARVIS to launch when you sign in to Windows; `remove_startup.bat` removes it.
