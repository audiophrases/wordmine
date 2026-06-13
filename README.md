# WordMine 🪓🔤

A playable 3D **voxel sandbox** (Minecraft-style) built to teach **English as a
Second Language**. You explore and mine a low-poly world; mining triggers
**ESL Challenges** where you *listen* to American-English narration, *choose*
the right word, practice *grammar*, and *speak* answers into your microphone.
Answer correctly to earn XP and building blocks. The goal isn't to beat the
game — it's to understand more English the longer you play.

> Built and tested on **Windows 11 + Python 3.14**.

---

## Quick start

**Option A — one click (recommended):**

1. Double-click **`setup_wordmine.bat`** (creates the venv, installs everything,
   downloads the offline speech model). Run once.
2. Double-click **`run_wordmine.bat`** to play.

**Option B — manual:**

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe setup_models.py    REM enables speaking challenges
.venv\Scripts\python.exe main.py
```

The first time a phrase is spoken it is fetched from Microsoft Edge's online
neural-TTS service and cached in `cache/tts/`; afterwards audio is instant and
works offline.

---

## Controls

| Action | Key |
| --- | --- |
| Move | **W A S D** |
| Jump | **Space** |
| Look | **Mouse** |
| Mine / break block | **Left click** |
| Place block | **Right click** |
| Select hotbar slot | **1–6** or **mouse wheel** |
| Word Journal (learned words) | **J** |
| Release / re-grab mouse (pause) | **Esc** |

**During a challenge:** press **1–4** to choose · **R** to replay the audio ·
hold **V** to speak into the mic · **Enter** to continue.

---

## How the learning loop works

1. **Mine glowing Word Ore** (the spinning gold blocks) — or just keep mining
   ordinary blocks; every few blocks also triggers a challenge.
2. A **challenge** appears. Types (all data-driven):
   - **Listen & Choose** — hear a definition, pick the matching word.
   - **Read & Match** — read a definition, pick the word.
   - **Say It!** — hear the word, then repeat it into your microphone.
   - **Grammar** — fill the blank with the correct word; hear the full sentence.
3. **Answer correctly** to gain **XP** and **+3 building blocks**. Get a word
   right twice and it's added to your **Word Journal** (press **J**).
4. A light **spaced-repetition** scheme re-asks weak/new words more often.
   Progress is saved to `progress.json`.

Speech is recognized **offline** with Vosk (no API key, no internet). Narration
uses **Microsoft Edge American-English neural voices** via `edge-tts`.

---

## Plugging in your own vocabulary & grammar

This is the whole point of the architecture — the game logic never hard-codes
content. Point `config.py` at your own files (you can list several; they merge):

```python
VOCAB_FILES   = [DATA_DIR / "vocabulary.json", DATA_DIR / "my_unit_5.json"]
GRAMMAR_FILES = [DATA_DIR / "grammar.json"]
```

**`vocabulary.json`**

```json
{
  "words": [
    {
      "id": "apple",
      "word": "apple",
      "phonetic": "/ˈæp.əl/",
      "part_of_speech": "noun",
      "definition": "a round fruit with red or green skin",
      "example": "I eat an apple every day.",
      "distractors": ["banana", "orange", "bread"],
      "category": "food",
      "level": 1
    }
  ]
}
```

Only `word` is strictly required. `distractors` become the wrong multiple-choice
options (missing ones are auto-filled from other words).

**`grammar.json`**

```json
{
  "rules": [
    {
      "id": "present_simple_3rd",
      "topic": "Present Simple",
      "prompt": "She ___ to school every day.",
      "options": ["go", "goes", "going", "gone"],
      "answer": "goes",
      "explanation": "Add -s for he / she / it.",
      "spoken": "She goes to school every day."
    }
  ]
}
```

`answer` must be one of `options`. `spoken` is read aloud after the player
answers. Bad entries are skipped with a console warning instead of crashing.

---

## Tuning

Everything tweakable lives in **`config.py`**:

- `TTS_VOICE` / `TTS_VOICE_ALT` — pick any American voice from `AMERICAN_VOICES`
  (e.g. `en-US-JennyNeural`, `en-US-GuyNeural`). `TTS_RATE` slows speech for
  beginners.
- `WORLD_RADIUS`, `WORD_ORE_COUNT`, `CHALLENGE_EVERY_N_MINES`, `XP_PER_CORRECT`.
- `SPEECH_MATCH_THRESHOLD` — how forgiving spoken-answer matching is (0–1).

---

## Architecture

```text
main.py            Wires everything together; gameplay input/update loop.
config.py          All tunables + data-source paths.
data/
  vocabulary.json  Seed vocabulary (swap for your own).
  grammar.json     Seed grammar rules.
game/              Voxel layer (Ursina) — kept separate from learning logic.
  blocks.py        Block-type registry.
  world.py         Voxel entity + procedural world generation.
  inventory.py     Hotbar inventory model.
  hud.py           Crosshair, hotbar, stats, subtitles, Word Journal.
esl/               Framework-agnostic learning engine (no Ursina imports here
                   except the UI module) — unit-testable in isolation.
  models.py        VocabWord / GrammarRule / Challenge dataclasses.
  loader.py        JSON -> typed models (the single data seam).
  engine.py        ChallengeFactory + spaced-repetition + grading + progress.
  tts.py           edge-tts worker thread, caching, MP3 playback.
  speech.py        Vosk + sounddevice push-to-talk recognition.
  challenge_ui.py  Modal challenge overlay (the only ESL module that uses Ursina).
```

**Adding a new challenge type:** add a constant in `esl/models.py`, a
`build_*` method in `ChallengeFactory` (`esl/engine.py`), and a render branch in
`esl/challenge_ui.py`. The game loop is untouched.

---

## Troubleshooting

- **No speech / "mic not set up":** run `python setup_models.py` to fetch the
  Vosk model, and make sure Windows lets apps use your microphone
  (Settings → Privacy → Microphone). The game stays fully playable without it.
- **No narration audio:** the *first* play of each phrase needs internet (Edge
  TTS). After that it's cached. Check the console for `[tts]` messages.
- **Stutter on first challenge:** that phrase is being generated/cached; it's
  instant next time. The cache is pre-warmed in the background at launch.
- **Reset progress:** delete `progress.json`.
