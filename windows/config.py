from pathlib import Path

APP_NAME = "J.A.R.V.I.S."
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "jarvis.db"
LOG_PATH = DATA_DIR / "jarvis.log"

# Everything below runs locally. Internet is only used by explicit web tools.
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2.5:1.5b"
VISION_MODEL = "llava:7b"  # Optional; install locally only if you want screen understanding.
EMBEDDING_MODEL = "nomic-embed-text"  # Optional local semantic document search.

SAMPLE_RATE = 16000
WHISPER_MODEL = "base.en"  # Change to small.en for better accuracy or tiny.en for more speed.
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
MIC_DEVICE = None

WAKE_MODEL_DIR = BASE_DIR / "models" / "vosk-model-small-en-us-0.15"
WAKE_WORD = "jarvis"

# Strict by default: every new request must begin with "Jarvis".
# Set to True if you want follow-up commands for SESSION_TIMEOUT_SECONDS after activation.
ENABLE_FOLLOWUP_SESSION = False
SESSION_TIMEOUT_SECONDS = 25

LISTEN_MAX_SECONDS = 15
LISTEN_START_TIMEOUT = 4.0
SILENCE_TIMEOUT = 1.15
VOICE_THRESHOLD = 0.008

MAX_PLAN_STEPS = 10
MAX_TOOL_RETRIES = 1

ENABLE_HUD = True
TTS_ENGINE = "sapi"  # "sapi" is stable. Set to "piper" to use the included Ryan model.
PIPER_MODEL = BASE_DIR / "voices" / "en_US-ryan-high.onnx"

# File tools are intentionally restricted to the signed-in user's profile.
ALLOW_OUTSIDE_USER_PROFILE = False
