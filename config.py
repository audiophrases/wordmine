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
# You can list multiple files; they are merged. See data/vocabulary.json for
# the expected schema (also documented in README.md).
# --------------------------------------------------------------------------
VOCAB_FILES = [DATA_DIR / "vocabulary.json"]

# --------------------------------------------------------------------------
# Text-to-speech  --  Microsoft Edge American English neural voices.
# --------------------------------------------------------------------------
TTS_ENABLED = True
TTS_VOICE = "en-US-AriaNeural"          # narrator: names objects/words
DISPATCH_VOICE = "en-US-ChristopherNeural"  # radio dispatcher: barks orders
TTS_VOICE_ALT = "en-US-GuyNeural"
TTS_RATE = "-8%"                        # a little slower; good for learners
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
# Free look / camera
# --------------------------------------------------------------------------
MOUSE_SENSITIVITY = 110       # was 40 -- higher = freer, snappier look
CAMERA_FOV = 95               # a touch wider for a more open feel
PLAYER_SPEED = 6.0
RUN_BOOST_MULT = 1.8          # speed multiplier while a "run" boost is active

# --------------------------------------------------------------------------
# Gameplay tuning
# --------------------------------------------------------------------------
XP_PER_CORRECT = 10
INTERACT_RANGE = 14           # how far the player can "see & hear" an object
SCAVENGE_TARGETS = ["key", "tool", "battery"]   # Zone 1 power-up items
PRAISE = ["Well done!", "Great job!", "Perfect!", "Excellent!", "Nice!"]

# Action-verb effect durations (seconds)
FREEZE_SECS = 5.0             # "stop" freezes a trap / the chaser
HIDE_SECS = 6.0              # "hide" makes the player invisible to the chaser
CLOSE_BLOCK_SECS = 4.0       # "close" slams a door, stalling the chaser
RUN_BOOST_SECS = 3.5         # "run" speed burst

# --------------------------------------------------------------------------
# The Chaser (Security Drone)
# --------------------------------------------------------------------------
CHASER_SPAWN_BEHIND = 5.0     # metres behind the player at level start
CHASER_BASE_SPEED = 2.4       # m/s (slower than the player -- escapable)
CHASER_ACCEL = 0.05          # m/s gained per second of chase (relentless)
CHASER_MAX_SPEED = 4.6
CHASER_CATCH_RADIUS = 1.4     # within this, you're Busted
CHASER_GRACE_SECS = 2.5       # head start before it begins moving

# --------------------------------------------------------------------------
# Radio dispatcher lines (spoken in DISPATCH_VOICE). Tune freely.
# --------------------------------------------------------------------------
DISPATCH = {
    "start": "Intruder alert! Security drone deployed. Move!",
    "zone1": "Find the key, the tool, and the battery to power the door.",
    "powered": "Power restored! Look at the door and tell it to open!",
    "zone2": "Path blocked. Use your words. Open! Stop! Run!",
    "zone3": "Final lock ahead. Say the word it demands!",
    "near": "It's right behind you! Run, or hide!",
    "hidden": "Good. Stay hidden.",
    "busted": "Intruder neutralized. Resetting.",
    "win": "You're clear! Great escape!",
}
DISPATCH_NEAR_COOLDOWN = 8.0  # min seconds between "it's behind you" warnings
