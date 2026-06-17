"""
Central configuration for WordMine.

WordMine is currently a peaceful audio-first ESL progression prototype: learners
listen to short English prompts and act in a 3D world. Teacher/designer tunables
live here so the runtime stays generic.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / "cache"
TTS_CACHE_DIR = CACHE_DIR / "tts"
MODELS_DIR = ROOT / "models"
VOSK_MODEL_DIR = MODELS_DIR / "vosk-model-small-en-us-0.15"
PROGRESS_FILE = ROOT / "progress.json"

# --------------------------------------------------------------------------
# Data sources -- plug your own JSON in here later.
# You can list multiple files; they are merged. See data/vocabulary.json for
# the expected schema.
# --------------------------------------------------------------------------
VOCAB_FILES = [DATA_DIR / "vocabulary.json"]

# --------------------------------------------------------------------------
# Text-to-speech -- Microsoft Edge American English neural voices.
# --------------------------------------------------------------------------
TTS_ENABLED = True
TTS_VOICE = "en-US-AriaNeural"          # guide/narrator voice
TTS_VOICE_ALT = "en-US-GuyNeural"       # reserved for future NPCs
TTS_RATE = "-8%"                        # a little slower; good for learners
TTS_VOLUME = "+0%"

AMERICAN_VOICES = [
    "en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural",
    "en-US-AnaNeural", "en-US-ChristopherNeural", "en-US-EricNeural",
    "en-US-MichelleNeural", "en-US-RogerNeural", "en-US-SteffanNeural",
]

# --------------------------------------------------------------------------
# Speech recognition -- optional future speaking mode. Disabled for the current
# listen + action beginner path.
# --------------------------------------------------------------------------
SPEECH_ENABLED = False
SPEECH_RECORD_SECONDS = 3.5
SPEECH_SAMPLE_RATE = 16000
SPEECH_MATCH_THRESHOLD = 0.6

# --------------------------------------------------------------------------
# Free look / camera
# --------------------------------------------------------------------------
MOUSE_SENSITIVITY = 110
CAMERA_FOV = 95
PLAYER_SPEED = 6.0

# --------------------------------------------------------------------------
# Peaceful ESL progression tuning
# --------------------------------------------------------------------------
XP_PER_CORRECT = 10
INTERACT_RANGE = 14           # how far the player can target a listen/action object
PRAISE = ["Well done!", "Great job!", "Perfect!", "Excellent!", "Nice!"]
