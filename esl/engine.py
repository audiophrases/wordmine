"""
Invisible spaced-repetition engine for the audio-only "See, Echo, Act" loop.

There is no quiz UI any more. The SRS no longer *asks* questions -- it *shapes
the world*: it decides which word a locked gate demands next, prioritising the
words the player is weakest at. Every spoken echo (success or failure) feeds the
same mastery model, so practice happens entirely through play.

`Progress` (the mastery/spaced-repetition core) is unchanged from before.
"""
from __future__ import annotations

import json
import random
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .models import VocabWord


# --------------------------------------------------------------------------
# Forgiving text matching for spoken (Vosk) answers
# --------------------------------------------------------------------------
def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def text_match(given: str, expected: str, threshold: float = 0.6) -> bool:
    """True if what Vosk heard is 'close enough' to the target word/phrase."""
    g, e = normalize(given), normalize(expected)
    if not g or not e:
        return False
    if e in g.split() or e in g:
        return True
    return SequenceMatcher(None, g, e).ratio() >= threshold


# --------------------------------------------------------------------------
# Mastery / spaced-repetition store (kept from the original design)
# --------------------------------------------------------------------------
class Progress:
    LEVEL_STEP = 50  # xp per level

    def __init__(self, path: Optional[Path] = None):
        self.path = path
        self.xp = 0
        self.total_correct = 0
        self.total_attempts = 0
        self.streak = 0
        self.best_streak = 0
        self.mastery: Dict[str, Dict[str, int]] = {}
        self.load()

    @property
    def level(self) -> int:
        return self.xp // self.LEVEL_STEP + 1

    @property
    def learned_ids(self):
        return {sid for sid, m in self.mastery.items() if m.get("streak", 0) >= 2}

    def seen_count(self, sid: str) -> int:
        return self.mastery.get(sid, {}).get("seen", 0)

    def record(self, source_id: str, correct: bool, xp: int):
        m = self.mastery.setdefault(source_id, {"seen": 0, "correct": 0, "streak": 0})
        m["seen"] += 1
        self.total_attempts += 1
        if correct:
            m["correct"] += 1
            m["streak"] += 1
            self.total_correct += 1
            self.xp += xp
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            m["streak"] = 0
            self.streak = 0
        self.save()

    def weight(self, source_id: str) -> float:
        """Higher = needs practice more (new or weak)."""
        m = self.mastery.get(source_id)
        if not m or m["seen"] == 0:
            return 3.0  # brand new material: introduce it
        accuracy = m["correct"] / m["seen"]
        if m.get("streak", 0) >= 2:
            return 0.4  # already learned: review occasionally
        return 1.0 + (1.0 - accuracy) * 2.0

    def load(self):
        if self.path and Path(self.path).exists():
            try:
                d = json.loads(Path(self.path).read_text(encoding="utf-8"))
                self.xp = d.get("xp", 0)
                self.total_correct = d.get("total_correct", 0)
                self.total_attempts = d.get("total_attempts", 0)
                self.best_streak = d.get("best_streak", 0)
                self.mastery = d.get("mastery", {})
            except (json.JSONDecodeError, OSError) as e:
                print(f"[progress] could not load, starting fresh: {e}")

    def save(self):
        if not self.path:
            return
        try:
            Path(self.path).write_text(
                json.dumps(
                    {
                        "xp": self.xp,
                        "total_correct": self.total_correct,
                        "total_attempts": self.total_attempts,
                        "best_streak": self.best_streak,
                        "mastery": self.mastery,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError as e:
            print(f"[progress] could not save: {e}")


# --------------------------------------------------------------------------
# SRS Director -- decides what the world should ask the player to say
# --------------------------------------------------------------------------
class SRSDirector:
    def __init__(
        self,
        words: List[VocabWord],
        progress_path: Optional[Path] = None,
        match_threshold: float = 0.6,
        xp_per_correct: int = 10,
    ):
        self.words = words
        self.by_id = {w.id: w for w in words}
        self.progress = Progress(progress_path)
        self.match_threshold = match_threshold
        self.xp_per_correct = xp_per_correct

    # -- grading -----------------------------------------------------------
    def accept(self, heard: str, target_word: str) -> bool:
        return text_match(heard, target_word, self.match_threshold)

    def record(self, word_id: str, correct: bool):
        xp = self.xp_per_correct if correct else 0
        self.progress.record(word_id, correct, xp)

    # -- selection (this is where SRS shapes the world) --------------------
    def demand_word(self, exclude: Iterable[str] = (), pool: Optional[Sequence[VocabWord]] = None) -> VocabWord:
        """
        Pick the word a gate/requirement should demand next, biased toward the
        player's weakest / newest vocabulary.
        """
        exclude = set(exclude)
        candidates = [w for w in (pool or self.words) if w.id not in exclude]
        if not candidates:
            candidates = list(pool or self.words)
        weights = [self.progress.weight(w.id) for w in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def weakest_words(self, n: int = 5) -> List[VocabWord]:
        return sorted(self.words, key=lambda w: -self.progress.weight(w.id))[:n]

    # -- misc --------------------------------------------------------------
    def word(self, word_id: str) -> Optional[VocabWord]:
        return self.by_id.get(word_id)

    def stats(self) -> Dict[str, int]:
        return {
            "xp": self.progress.xp,
            "level": self.progress.level,
            "learned": len(self.progress.learned_ids),
            "total_words": len(self.words),
            "streak": self.progress.streak,
        }

    def speakable_texts(self) -> List[str]:
        """Everything the narrator might say -- used to pre-bake TTS at boot."""
        return [w.word for w in self.words]
