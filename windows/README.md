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

## Windows work, Gmail and account workflows (experimental)

JARVIS can now create new Excel (.xlsx), Word (.docx), PowerPoint (.pptx), and CSV files using purpose-built registered tools. These files are generated directly and do not require Microsoft Office to be installed. Existing files are not intentionally overwritten.

Try: “Jarvis, create an Excel file in Documents called expenses.xlsx with columns Item and Cost and rows Rent 800, Internet 50.”

### Connect Gmail securely (optional)

1. Enable the Gmail API in a Google Cloud project and configure a Desktop OAuth client and consent screen.
2. Download the Desktop OAuth client JSON and KEEP IT OUT OF THE PUBLIC REPOSITORY.
3. Activate the Windows virtual environment, then run: python setup_gmail.py PATH_TO_DESKTOP_OAUTH_CLIENT_JSON
4. Finish Google's browser sign-in. OAuth tokens are saved in Windows Credential Manager through keyring.
5. Try: “Jarvis, summarise my inbox from the last 24 hours.”

Gmail can list and read messages from the last 24 hours, prepare local drafts, and send a prepared draft only after an explicit on-screen confirmation showing its recipient, subject and body. Drafts are held in JARVIS memory, not saved in Gmail's Drafts folder. An OAuth Desktop client is required; never put email passwords, authentication codes, client JSON or access tokens into config.py or GitHub.

### Website accounts

Open a website in JARVIS's controlled Chromium browser, then sign in MANUALLY. Your browser profile remains locally in windows/data/browser_profile. Ask JARVIS to summarise the currently open signed-in page, or help navigate it. Website clicks now require confirmation. Do not dictate passwords or verification codes to JARVIS; perform high-risk purchases, payments, account changes and MFA manually.

### Languages and speed

The multilingual Faster-Whisper model is now set to base with automatic language detection. Set WHISPER_LANGUAGE in config.py to en, es, fr, de or another supported code to override detection. The Vosk wake word remains English “Jarvis”. Model tiny is faster but less accurate; model small is more accurate but slower. Shorter reply lengths and quicker speech decoding should help response times, depending on your hardware.

### Verification

From the Windows virtual environment, run:

    python -m compileall -q .
    python -m unittest discover -s tests -v

The new features are still experimental until tested on a real Windows PC. The macOS folder has not been changed for this upgrade.

## Command recognition troubleshooting (Windows)

JARVIS routes common work and Gmail commands directly before using a focused
local AI planner for complex documents. Use the JARVIS text-input field
first to distinguish voice-transcription errors from action-routing errors.

Examples you can type or say after waking JARVIS:

- Create an Excel spreadsheet in Documents named expenses.xlsx with columns Item and Cost and rows Rent 800, Internet 50
- Make a CSV called inventory.csv on Desktop with columns Item and Count and rows Pens 5, Pencils 12
- Create a Word report called quarterly.docx about our project priorities
- Make a PowerPoint presentation named briefing.pptx about project updates
- Summarise my emails from the last 24 hours (requires Gmail OAuth setup)
- Draft an email to team@example.org about our weekly meeting
- Send the email (reviews the most recent draft and asks for confirmation)
- Summarize this account dashboard (after signing in manually in JARVIS browser)

Excel/CSV direct commands need the filename, columns, and optional rows.
Word/PowerPoint can generate content using the local model, but require
explicit filenames (.docx/.pptx). JARVIS refuses to overwrite existing
work files: use a new filename for subsequent runs.

For fast spoken English commands, if the multilingual model transcribes
incorrectly, set WHISPER_LANGUAGE = "en" in config.py and restart JARVIS.
Set it back to "auto" or another supported language code for other
languages. Wake word detection still expects the English name Jarvis.

From the Windows folder with .venv active, run:

    python -m unittest discover -s tests -v

Command routing, generated documents, and local email draft previews are
tested without sending emails, accessing a website account, or making
payments. Gmail still requires valid account authorization and real UI testing.
