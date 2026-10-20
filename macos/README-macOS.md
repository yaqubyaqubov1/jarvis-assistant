# JARVIS macOS — experimental replacement files

These are **complete replacement text files** based on the previously uploaded
`Jarvis(1).zip` Windows project. They have been statically checked on Linux but
**not executed on a real Mac**. Do not call this a tested Mac release.

## Replace files

1. Make a backup of your `jarvis-assistant` folder. Do **not** overwrite the Windows edition.
2. Copy the contents of this ZIP into your **Mac copy** of `jarvis-assistant/`,
   allowing files with matching names to be replaced. Preserve all other
   project modules, `main.py`, `ui/core_widget.py`, etc.
3. Preserve `models/vosk-model-small-en-us-0.15/`; it is deliberately **not**
   included in this text-only archive.
4. The optional Piper `.onnx` voice is omitted. macOS uses native `say` by default.

## Install on a Mac

Install Python **3.11** from python.org and Ollama from ollama.com. In Terminal (zsh):

```zsh
cd ~/Desktop/Jarvis/jarvis-assistant
zsh setup_macos.command
ollama pull qwen2.5:1.5b
ollama pull llava:7b  # optional for screen vision
zsh Jarvis-debug.command
```

If Ollama reports connection refused, open the Ollama application first.
Your microphone may require selection through `MIC_DEVICE` in `config.py`.

Grant the process running JARVIS (Terminal when running from source; the JARVIS
app when packaged) the required permissions in **System Settings → Privacy & Security**:
**Microphone**, **Accessibility**, and **Screen & System Audio Recording**
(also called Screen Recording on earlier macOS versions). Some macOS
Apple Events or Music controls may request **Automation** permission.
Quit/reopen Terminal or JARVIS after approving new permissions.

## Optional Piper Ryan voice

```zsh
source .venv/bin/activate
python -m pip install -r requirements-optional-macos.txt
python download_voice.py
```

Set `TTS_ENGINE = "piper"` in `config.py`. The model is not stored in GitHub.
The Piper API may vary by version; the default macOS `say` voice is the
recommended fallback.

## Known Mac limitations

- App discovery uses common `.app` folders and LaunchServices; App Store apps
  and games with unusual launchers may need aliases.
- Screen automation requires Accessibility and Screen Recording permissions.
  Retina coordinate conversion is an approximation; multi-monitor displays
  must be tested separately.
- Play/pause/next/previous target **Music.app**; not all media players.
- Brightness percentage requires optional `brightness` CLI (`brew install brightness`)
  and may not support external displays.
- CPU temperature often shows **Unavailable** on macOS.
- An app-launch request is not proof that its window appeared.
- App closing uses graceful quit requests; no force kills. Unsaved documents
  can cause native prompts.
- The native PySide6 menu-bar icon varies by macOS version. Mac Dock/menu
  integration and audio input require actual hardware testing.
- Screen-task high-risk actions are intentionally blocked in the visual loop.
- This is a source-code setup, not a signed/notarized `.app` installer.

## Windows separation and privacy

This ZIP does not contain your personal `data/jarvis.db`, logs or browser profile.
macOS runtime data goes to `~/Library/Application Support/JARVIS/`.
Do not run the Windows `.bat` launchers on Mac. Keep the Windows requirements
and Windows version on a separate branch or directory.

## Run static checks

```zsh
python3.11 -m compileall -q .
python3.11 -m unittest discover -s tests_macos -v
```

These checks do not validate accessibility, microphone, Ollama availability,
or actual mouse clicks. Run the smoke checklist on a real Mac.
