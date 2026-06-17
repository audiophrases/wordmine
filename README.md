# WordMine 🎧 — ESL Listening Rooms

WordMine is now a **peaceful audio-first 3D ESL prototype**. Beginner learners
hear short English prompts and act in the world: look at an object, touch it,
open room gates, and move into the next level. There is **no chase**, **no alarm
pressure**, **no busted/reset state**, and no required speaking in the first
learning path.

The design goal is simple:

> **Listen → understand → act → hear helpful feedback.**

Mistakes are treated as more comprehensible input, not punishment. If the learner
touches the wrong object, the guide says the object name and repeats the target,
for example: *"Cup. Apple."* The learner can try again.

> Total Physical Response (TPR) for A1–A2 learners. Built & tested on
> **Windows 11 + Python 3.14**.

---

## The loop: **Listen · Aim · Act**

- **Listen** — the guide speaks one short prompt.
- **Aim** — look at the matching 3D object or glowing gate.
- **Act** — click, press **E**, or press **Space**.
- **Feedback** — correct actions glow/animate and advance the course; wrong
  actions name the object and repeat the target prompt.

There is no visible gameplay text. The reticle and object marker are icon/color
feedback only.

---

## Levels vs rooms

A **level** is a full course map. A **room** is a section inside that level.

Current implementation:

- **Level 1** has three rooms:
  - Room 1: first words — apple, cup, ball, book
  - Room 2: find/touch — key, box, table, basket
  - Room 3: review — robot, apple, cup, book, ball
- **Level 2** is now implemented and loads after Level 1:
  - Room 1: banana, chair, shoe, car
  - Room 2: bed, dog, table, basket
  - Room 3: color/size apples, placement practice, and review
    - red apple / green apple
    - big apple / small apple
    - “Put the red apple in the basket.”
    - “Put the green apple on the table.”
    - “Put the big apple in the box.”
    - “Put the small apple on the chair.”

Room doors do **not** open automatically. At room transitions the guide says:

- “Go to the next room.”

The learner then finds the glowing gate, aims until the reticle turns gold, and
clicks / presses **E** / presses **Space** to open it.

At the end of Level 1, the guide says:

- “Go to the next level.”

The learner opens the final glowing gate and WordMine loads Level 2. Level 2 is
the current end of the playable prototype.

### Grab and place

Some Level 2 prompts now require two actions:

1. Aim at the requested object and act to pick it up.
2. Aim at the requested place and act again to put it there.

For example, “Put the red apple in the basket” means the learner picks up the
red apple, then targets the basket. The object follows the learner while carried.
Wrong objects or wrong places only trigger gentle audio feedback and allow retry.

---

## Quick start

**One click:** run **`setup_wordmine.bat`** once, then **`run_wordmine.bat`**.

**Manual:**

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

On the first run, narration is pre-baked and cached with Edge TTS. After that,
voice cues play from the local cache.

---

## Controls

- Move / look / jump: **W A S D**, **Mouse**, **Space**
- Act on the highlighted object, gate, or placement target: **Left click**, **E**, or **Space**
- Carry/place flow: act once on the named object to pick it up, then act on the named place to put it down
- Replay the current prompt: **R**
- Release / re-grab mouse: **Esc**, then click

Reticle states:

- white: no target
- gold: target available
- cyan ring: reserved for future speaking/listening modes

---

## Plug in your own words

Point `VOCAB_FILES` in [config.py](config.py) at your JSON. A noun becomes a 3D
object by adding a `world_object` shape:

```json
{
  "id": "apple",
  "word": "apple",
  "world_object": {
    "shape": "apple",
    "color": [0.90, 0.12, 0.10],
    "scale": 1.0
  }
}
```

Current built-in shapes include:

- `apple`
- `banana`
- `basket`
- `ball`
- `bed`
- `big_apple`
- `book`
- `box`
- `car`
- `chair`
- `cup`
- `dog`
- `green_apple`
- `house`
- `key`
- `red_apple`
- `robot`
- `shoe`
- `small_apple`
- `sphere`
- `table`

The current prompt sequences live in `LEVEL_PROMPTS` in [main.py](main.py).
The level and room layouts live in [game/level.py](game/level.py).

---

## Architecture

```text
main.py                Orchestration: free-look, targeting, level prompt
                       sequences, listen→act validation, calm feedback,
                       manual room gates, carry/place prompts, and
                       Level 1 → Level 2 loading.
config.py              Tunables: mouse, camera, voices, audio cache, data files.
data/vocabulary.json   Beginner concrete words + 3D object specs.
game/
  level.py             Level maps with three peaceful ESL rooms each.
  interactables.py     Raycastable Interactable + low-poly prop builders.
  drone.py             Companion drone guidance animation.
  hud.py               Text-free HUD: reticle, loading bar, progress pips.
esl/
  engine.py            Progress/spaced repetition store and word lookup.
  tts.py               Edge TTS worker and cache.
  sfx.py               Synthesized success/select/fail/win cues.
  loader.py / models.py   JSON -> VocabWord.
tests/
  test_lesson_progression.py   Regression checks for manual gates and Level 2.
```

`game/chaser.py` remains in the repository as legacy code, but the current
runtime does not import or use it.

---

## Verification

Useful checks from the repo root:

```bat
.venv\Scripts\python.exe tests\test_lesson_progression.py
.venv\Scripts\python.exe -m py_compile main.py config.py game\level.py game\interactables.py game\hud.py esl\sfx.py esl\engine.py esl\loader.py esl\models.py
set WORDMINE_SELFTEST=1
.venv\Scripts\python.exe main.py
```

In Git Bash, use POSIX syntax instead:

```bash
WORDMINE_SELFTEST=1 .venv/Scripts/python.exe main.py
```

---

## Troubleshooting

- **No audio on first run:** pre-baking needs internet once for Edge TTS. After
  that, cached voice clips work locally.
- **Gate does not open:** aim at the glowing gate until the reticle turns gold,
  then left-click or press **E**. The guide prompt will be “Go to the next room”
  or “Go to the next level,” not “open the door.”
- **Too fast / too slow movement:** tune `PLAYER_SPEED`, `MOUSE_SENSITIVITY`, and
  `CAMERA_FOV` in `config.py`.
- **Reset learning progress:** delete `progress.json`.
- **Want speaking practice later:** `config.py` keeps the speech-recognition
  settings, but `SPEECH_ENABLED` is currently `False` because the first upgrade
  is listen + action only.
