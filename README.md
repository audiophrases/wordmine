# WordMine 🎙️🚨 — Heist Protocol

An **audio-only** ESL game: a high-tension **escape/heist** where you learn English
by *speaking* under pressure. There is **no on-screen text**. A companion drone
names the object you look at (Microsoft Edge American TTS), and you act by
repeating the word into your mic (offline Vosk). A relentless **Security Drone**
hunts you the whole time.

> Total Physical Response (TPR) for A1–A2 learners. Built & tested on
> **Windows 11 + Python 3.14**.

---

## The loop: **See · Hear · Echo · Act**

- **See / Hear** — look at a thing; the companion drone flies to it and speaks
  its English word.
- **Echo** — hold **V** and say the word. Offline Vosk checks your pronunciation.
- **Act** — nouns are **collected**; **verbs change the world**:

| Say | Looking at… | Effect |
| --- | --- | --- |
| **"open"** | a glowing door / barrier | clears the path |
| **"close"** | the wall console | slams a door, stalling the chaser |
| **"stop"** | the moving trap **or the Security Drone** | freezes it for 5 s |
| **"hide"** | the safe-house | you vanish from the chaser for a few seconds |
| **"run"** | the green floor pad | a speed burst |

If the Security Drone reaches you, it's **Busted** — failure cue, and the level
resets. A heartbeat accelerates and the screen reddens as it closes in.

---

## Three zones

1. **Scavenge** — find & echo **key**, **tool**, **battery** to power the first
   door, while dodging the drone.
2. **The Chase** — a corridor of action-verb obstacles: *open* a door, *stop* a
   sliding trap, hit a *run* pad, *hide*, or *close* a door behind you.
3. **The Lockout** — the final gate. The **SRS engine demands your weakest word**
   under pressure; say it to open the gate, then reach the trophy to escape.

A radio **dispatcher** (a second American voice) barks orders: *"Intruder alert!
Run!"*, *"Tell the door to open!"*

---

## Quick start

**One click:** run **`setup_wordmine.bat`** once (venv + deps + speech model),
then **`run_wordmine.bat`**.

**Manual:**

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe setup_models.py     REM offline mic recognition
.venv\Scripts\python.exe main.py
```

On the first run, all narration is **pre-baked and cached** (a loading bar shows
progress; needs internet once). Afterwards every cue plays **instantly and
offline**.

---

## Controls

| Action | Input |
| --- | --- |
| Move / look / jump | **W A S D**, **Mouse**, **Space** |
| **Echo** a word | **hold V**, speak, release |
| Replay the word | **R** |
| Release / re-grab mouse | **Esc** |

Reticle: **white** = nothing, **gold** = something you can echo, **cyan** =
listening. No mic set up? Pressing **V** auto-accepts so the heist is still
walkable. Run `setup_models.py` to enable real speaking.

**Free look** feels much freer now (`MOUSE_SENSITIVITY` 110, FOV 95 in
`config.py` — tune to taste).

---

## Plug in your own words (modular)

Point `VOCAB_FILES` in [config.py](config.py) at your JSON. A noun becomes a 3D
collectable by adding a `world_object`; verbs are placed on doors/traps/hide-spots
by the level builder.

```json
{ "id": "key", "word": "key",
  "world_object": { "shape": "key", "color": [0.90, 0.72, 0.15], "scale": 1.0 } }
```

Built-in `shape`s: `key`, `tool`, `battery`, `dog`, `house`, `shadow`, `sphere`
(add more in `game/interactables.py`). Tune the chase, zones, verb durations and
dispatcher lines in [config.py](config.py).

---

## Architecture

```text
main.py                Orchestration: free-look, targeting, chase, verbs, zones,
                       Busted/reset, dispatcher, boot loading.
config.py              All tunables: mouse, chaser, durations, dispatcher lines.
data/vocabulary.json   Scavenge nouns + action verbs (+ optional 3D shapes).
game/
  level.py             Structured 3-zone facility (rebuilt on each attempt).
  chaser.py            Security Drone: breadcrumb homing, freeze/hide/block, catch.
  interactables.py     Verb-aware Interactable + finer, natural prop builders.
  drone.py             Companion drone (guidance + "voice").
  hud.py               Text-free HUD: reticle, listening ring, danger vignette, pips.
esl/
  engine.py            Progress (spaced repetition) + SRSDirector (demands words).
  tts.py               Edge TTS worker, cache, dual-voice boot pre-bake.
  speech.py            Vosk + sounddevice push-to-talk recognition.
  sfx.py               Synthesized cues: heartbeat, alarm, busted, success…
  loader.py / models.py   JSON -> VocabWord.
```

---

## Troubleshooting

- **Speaking does nothing / "auto-accepts":** run `python setup_models.py` and
  allow microphone access (Windows Settings → Privacy → Microphone).
- **No audio on first run:** pre-baking needs internet once (Edge TTS). After
  that it's fully offline and instant.
- **Too hard / too easy:** tune `CHASER_BASE_SPEED`, `CHASER_ACCEL`,
  `CHASER_GRACE_SECS`, `FREEZE_SECS`, etc. in `config.py`.
- **Reset learning progress:** delete `progress.json`.
