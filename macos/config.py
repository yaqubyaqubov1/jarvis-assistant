"""Settings for JARVIS macOS experimental port."""
from pathlib import Path

APP_NAME = "J.A.R.V.I.S."
BASE_DIR = Path(__file__).resolve().parent
# Keep mutable files out of the source tree and, later, out of .app bundles.
DATA_DIR = Path.home() / "Library" / "Application Support" / "JARVIS"
DB_PATH = DATA_DIR / "jarvis.db"
LOG_PATH = DATA_DIR / "jarvis.log"

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2.5:1.5b"
VISION_MODEL = "llava:7b"
EMBEDDING_MODEL = "nomic-embed-text"

SAMPLE_RATE = 16000
WHISPER_MODEL = "base.en"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
MIC_DEVICE = None

WAKE_MODEL_DIR = BASE_DIR / "models" / "vosk-model-small-en-us-0.15"
WAKE_WORD = "jarvis"
ENABLE_FOLLOWUP_SESSION = False
SESSION_TIMEOUT_SECONDS = 25
LISTEN_MAX_SECONDS = 15
LISTEN_START_TIMEOUT = 4.0
SILENCE_TIMEOUT = 1.15
VOICE_THRESHOLD = 0.008
MAX_PLAN_STEPS = 10
MAX_TOOL_RETRIES = 1
ENABLE_HUD = True
# 'say' is built into macOS. 'piper' requires optional piper-tts and voice files.
TTS_ENGINE = "say"
PIPER_MODEL = BASE_DIR / "voices" / "en_US-ryan-high.onnx"
ALLOW_OUTSIDE_USER_PROFILE = False
