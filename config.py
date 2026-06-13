"""
Central configuration for WordMine.

Tweak gameplay, voices, and data sources here. Everything that a teacher or
designer might want to change lives in this one file so the rest of the code
stays generic.
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
# Data sources  --  plug your own JSON in here later.
# You can list multiple files; they are merged. See data/vocabulary.json and
# data/grammar.json for the expected schema (also documented in README.md).
# --------------------------------------------------------------------------
VOCAB_FILES = [DATA_DIR / "vocabulary.json"]
GRAMMAR_FILES = [DATA_DIR / "grammar.json"]

# --------------------------------------------------------------------------
# Text-to-speech  --  Microsoft Edge American English neural voices.
# --------------------------------------------------------------------------
TTS_ENABLED = True
TTS_VOICE = "en-US-AriaNeural"      # main narrator (female, American)
TTS_VOICE_ALT = "en-US-GuyNeural"   # alternate speaker (male, American)
TTS_RATE = "-8%"                    # a little slower; good for learners
TTS_VOLUME = "+0%"

# Other American English voices you can drop into TTS_VOICE / TTS_VOICE_ALT:
AMERICAN_VOICES = [
    "en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural",
    "en-US-AnaNeural", "en-US-ChristopherNeural", "en-US-EricNeural",
    "en-US-MichelleNeural", "en-US-RogerNeural", "en-US-SteffanNeural",
]

# --------------------------------------------------------------------------
# Speech recognition (the player speaks into the mic)
# --------------------------------------------------------------------------
SPEECH_ENABLED = True
SPEECH_RECORD_SECONDS = 3.5
SPEECH_SAMPLE_RATE = 16000
SPEECH_MATCH_THRESHOLD = 0.6   # 0..1 fuzzy ratio required to accept a spoken answer

# --------------------------------------------------------------------------
# Gameplay tuning
# --------------------------------------------------------------------------
WORLD_RADIUS = 14              # half-width of the ground (in blocks)
WORD_ORE_COUNT = 16           # glowing "Word Ore" challenge blocks in the world
CHALLENGE_EVERY_N_MINES = 10  # a challenge also pops every N ordinary blocks mined
XP_PER_CORRECT = 10
PLAYER_START_HEIGHT = 6
