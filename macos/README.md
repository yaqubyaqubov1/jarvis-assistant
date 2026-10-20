# J.A.R.V.I.S. — Local macOS Desktop Agent

J.A.R.V.I.S. is a locally powered AI desktop assistant designed to understand voice commands, answer questions, manage tasks, and interact with your Mac.

It runs using local speech recognition and Ollama AI models. **No cloud AI API key is required.**

> **Development status:** The macOS version is experimental and currently incomplete. Several required modules are missing from the repository. Installation instructions are provided below, but the application may not launch until the macOS port is completed.

## Core behavior

- JARVIS uses a local Vosk wake-word detector to listen for **"Jarvis"**.
- Audio spoken before activation is discarded rather than passed to Whisper.
- By default, each new voice command requires the wake word again.
- Faster-Whisper transcribes spoken commands locally.
- Ollama and Qwen handle local conversation and AI-assisted task planning.
- Sensitive system actions are intended to pass through permissions and confirmation checks.
- The assistant uses a PySide6 graphical interface.

## Features

The macOS edition is intended to provide the following features as development is completed:

- Local AI conversations and general knowledge
- Voice activation and speech recognition
- Natural voice responses
- Multi-step task planning and execution
- Application launching and closing
- Mouse, keyboard, and clipboard controls
- Screenshots and optional AI screen understanding
- Web browsing and search
- File and folder management
- Document reading and local knowledge search
- System information and basic Mac controls
- SQLite memory and task history
- Timers and reminders
- Custom Python skills
- JARVIS graphical interface with animated states
- Optional Piper voice support
- Permission checks and confirmation before sensitive actions

**Important:** These are the intended capabilities of the Mac port, not a claim that every feature currently works.

## System requirements

- A compatible Mac running a supported version of macOS
- Apple Silicon or Intel processor with a compatible Python and PySide6 build
- Python **3.11** recommended
- Ollama for macOS
- Internet connection for initial software and model downloads
- Microphone for voice commands
- Sufficient available storage and RAM for local AI models

## Installation

### 1. Install Python

Install Python 3.11 from [python.org](https://www.python.org/downloads/).

Verify the installation in Terminal:

```zsh
python3 --version
```

### 2. Install Ollama

Download Ollama from [ollama.com](https://ollama.com).

Open Ollama, then download the main AI model:

```zsh
ollama pull qwen2.5:1.5b
```

Optional screen-vision model:

```zsh
ollama pull llava:7b
```

Optional semantic document search model:

```zsh
ollama pull nomic-embed-text
```

### 3. Download JARVIS

Clone the repository:

```zsh
git clone https://github.com/yaqubyaqubov1/jarvis-assistant.git
```

Enter the macOS folder:

```zsh
cd jarvis-assistant/macos
```

Alternatively, download the repository ZIP from GitHub and open the `macos` folder in Terminal.

### 4. Create a Python virtual environment

```zsh
python3 -m venv .venv
source .venv/bin/activate
```

Verify that the environment uses a compatible Python version:

```zsh
python --version
```

### 5. Install dependencies

```zsh
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

Install the Playwright browser:

```zsh
python -m playwright install chromium
```

If PySide6 cannot be installed, check your Python version, macOS version, and processor architecture before proceeding.

### 6. Configure macOS permissions

JARVIS may require permissions to control applications, capture the screen, and use the microphone.

Open **System Settings → Privacy & Security** and review:

- **Microphone** — voice recognition
- **Accessibility** — mouse and keyboard automation
- **Screen & System Audio Recording** or **Screen Recording** — screenshots and visual tasks
- **Automation** — control of supported Mac applications, when requested

Permissions may need to be granted to Terminal when launching JARVIS from source.

Restart Terminal or JARVIS after changing permissions if necessary.

## Starting JARVIS

Once the missing macOS modules have been restored and the port is working, launch from the `macos` folder:

```zsh
source .venv/bin/activate
python main.py
```

Make sure Ollama is running first.

**Current known startup issue:** The repository is missing `ui/main_window.py`, `config.py`, `voice/speech.py`, `voice/tts.py`, and other modules. These must be restored or replaced with Mac-compatible versions before normal startup is possible.

## Suggested test order

After completing the macOS port, test features gradually:

1. Say **"Jarvis"**, then **"hello"**.
2. Say **"Jarvis"**, then **"what time is it?"**
3. Say **"Jarvis"**, then **"open Safari"**.
4. Say **"Jarvis"**, then **"remind me in two minutes to drink water"**.
5. Say **"Jarvis"**, then **"create a folder called AI Projects on my desktop"**.
6. Say **"Jarvis"**, then **"what is recursion?"**
7. Say **"Jarvis"**, then **"take a screenshot"**.
8. Optionally say **"Jarvis"**, then **"describe my screen"**.

Start with the GUI, microphone, and AI conversation before testing desktop automation.

## Voice recognition

JARVIS uses Vosk for local wake-word recognition and Faster-Whisper for speech transcription.

The repository includes the Vosk English model:

`models/vosk-model-small-en-us-0.15/`

Faster-Whisper may need to download its speech model during the first run.

If JARVIS uses the wrong microphone, check the available audio devices:

```zsh
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Microphone selection can be configured once the macOS `config.py` file has been restored.

## Text-to-speech

macOS provides a built-in speech engine through the `say` command.

You can test it independently:

```zsh
say "Good evening. JARVIS speech systems are ready."
```

The macOS port is intended to support native speech as a default, with optional Piper voice synthesis.

### Optional Piper voice

The repository includes a script named `download_voice.py` and voice configuration metadata.

To download the optional Piper model, run:

```zsh
python download_voice.py
```

This does not by itself enable Piper. The compatible speech implementation and any additional Piper dependencies must also be installed and configured.

## Safety and privacy

JARVIS is designed around local AI processing and controlled desktop actions.

The intended safety measures include:

- Only registered tools can perform actions.
- Sensitive operations require user confirmation.
- File deletion should use Trash instead of permanent deletion.
- The assistant should not have unrestricted shell access.
- Mouse automation should retain PyAutoGUI's emergency failsafe.
- Screen capture and app control require macOS permissions.

Some of these protections depend on modules that are not yet present in the macOS port. **Do not use unfinished desktop automation for important files or applications.**

Voice processing and AI conversations can run locally once models are installed. Web searches, model downloads, and other explicitly online tasks require internet access.

## Known macOS limitations

- This is an experimental port, not a finished macOS release.
- Several necessary Python modules are currently missing.
- Some original Windows features need macOS-specific implementations.
- macOS app launching differs from Windows executable launching.
- Desktop automation requires Accessibility permission.
- Screen understanding requires Screen Recording permission.
- Some keyboard shortcuts must use **Command** instead of **Ctrl**.
- Retina displays and multiple monitors require additional testing.
- Mac system controls and hardware monitoring vary by model.
- Ollama must be installed and running separately.
- No signed or notarized `.app` installer is currently provided.

## Troubleshooting

**`No module named 'ui.main_window'`**

The interface module is missing from the macOS folder. A compatible `ui/main_window.py` must be added.

**`No module named 'config'`**

The macOS `config.py` file is missing.

**`No matching distribution found for PySide6`**

Verify Python, macOS, and processor compatibility:

```zsh
python --version
sw_vers -productVersion
uname -m
```

Then upgrade pip:

```zsh
python -m pip install --upgrade pip
```

**Ollama connection error**

Make sure Ollama is running:

```zsh
ollama list
```

**Microphone not working**

Check microphone permissions and verify that the correct input device is selected.

**Permission denied**

Grant the required macOS permissions to Terminal or the application running JARVIS.

## Windows version

The Windows edition is available separately in the [`windows/`](../windows/) directory.

Windows users should follow the Windows README and use the `.bat` setup and launcher files.

Do not use Windows `.bat` scripts on macOS.

## Contributing

The macOS edition is under development. Contributions, testing, bug reports, and improvements are welcome.

Repository: https://github.com/yaqubyaqubov1/jarvis-assistant

---

**J.A.R.V.I.S. — Your local AI desktop assistant.**

*macOS edition — experimental development build.*
