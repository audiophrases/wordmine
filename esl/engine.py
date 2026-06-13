"""
The modular challenge engine.

`ChallengeFactory` turns a VocabWord or GrammarRule into a presentable
`Challenge`. `ChallengeManager` decides *which* challenge to show next (a light
spaced-repetition scheme), grades answers, and tracks the learner's progress.

To add a new challenge kind:
  1. add a type constant in models.py,
  2. add a `_build_*` method here and register it in ChallengeFactory,
  3. render it in esl/challenge_ui.py.
Nothing in the game loop needs to change.
"""
from __future__ import annotations

import json
import random
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional

from . import models
from .models import (
    Challenge,
    ChallengeResult,
    GrammarRule,
    VocabWord,
)


# --------------------------------------------------------------------------
# Text matching helper (shared with the speech recogniser)
# --------------------------------------------------------------------------
def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def text_match(given: str, expected: str, threshold: float = 0.6) -> bool:
    """Fuzzy, forgiving comparison used for spoken answers."""
    g, e = normalize(given), normalize(expected)
    if not g:
        return False
    if e and e in g.split():
        return True
    if e and e in g:
        return True
    return SequenceMatcher(None, g, e).ratio() >= threshold


# --------------------------------------------------------------------------
# Challenge construction
# --------------------------------------------------------------------------
class ChallengeFactory:
    """Builds Challenge objects from source data."""

    def __init__(self, words: List[VocabWord], speech_available: bool = True):
        self.words = words
        self.speech_available = speech_available

    def _options_for(self, word: VocabWord, k: int = 3) -> List[str]:
        pool = [d for d in word.distractors if normalize(d) != normalize(word.word)]
        if len(pool) < k:
            others = [w.word for w in self.words if w.id != word.id]
            random.shuffle(others)
            for o in others:
                if len(pool) >= k:
                    break
                if normalize(o) not in {normalize(word.word)} | {normalize(p) for p in pool}:
                    pool.append(o)
        options = pool[:k] + [word.word]
        random.shuffle(options)
        return options

    def build_listen_and_choose(self, word: VocabWord) -> Challenge:
        return Challenge(
            type=models.LISTEN_AND_CHOOSE,
            title="Listen & Choose",
            instruction="Listen to the meaning, then choose the word.  [R] replays the audio.",
            prompt_text=word.definition,
            spoken_text=word.definition,
            options=self._options_for(word),
            answer=word.word,
            explanation=f"{word.word}  {word.phonetic}\n{word.definition}",
            hide_prompt_text=True,
            source_id=word.id,
            meta={"reveal_spoken": word.example or word.word},
        )

    def build_definition_match(self, word: VocabWord) -> Challenge:
        return Challenge(
            type=models.DEFINITION_MATCH,
            title="Read & Match",
            instruction="Read the meaning and choose the matching word.",
            prompt_text=word.definition,
            spoken_text=word.definition,
            options=self._options_for(word),
            answer=word.word,
            explanation=f"{word.word}  {word.phonetic}\nExample: {word.example}",
            source_id=word.id,
            meta={"reveal_spoken": word.example or word.word},
        )

    def build_speak_the_word(self, word: VocabWord) -> Challenge:
        return Challenge(
            type=models.SPEAK_THE_WORD,
            title="Say It!",
            instruction="Hold [V] and say the word into your microphone.",
            prompt_text=f"{word.word}\n{word.phonetic}\n\n{word.definition}",
            spoken_text=word.word,
            options=[],
            answer=word.word,
            explanation=f"Great pronunciation practice!\nExample: {word.example}",
            accepts_speech=True,
            source_id=word.id,
            meta={"reveal_spoken": word.example or word.word},
        )

    def build_grammar_fill(self, rule: GrammarRule) -> Challenge:
        return Challenge(
            type=models.GRAMMAR_FILL,
            title=f"Grammar: {rule.topic}",
            instruction="Choose the word that correctly fills the blank.",
            prompt_text=rule.prompt,
            spoken_text="",  # spoken only on reveal (the full correct sentence)
            options=list(rule.options),
            answer=rule.answer,
            explanation=rule.explanation,
            source_id=rule.id,
            meta={"reveal_spoken": rule.spoken or rule.prompt.replace("___", rule.answer)},
        )

    def for_word(self, word: VocabWord) -> Challenge:
        builders = [self.build_listen_and_choose, self.build_definition_match]
        if self.speech_available:
            # weight speaking a little higher -- it's the signature mechanic
            builders += [self.build_speak_the_word, self.build_speak_the_word]
        return random.choice(builders)(word)


# --------------------------------------------------------------------------
# Progress / mastery tracking
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
        # per source id: {"seen": n, "correct": n, "streak": n}
        self.mastery: Dict[str, Dict[str, int]] = {}
        self.load()

    @property
    def level(self) -> int:
        return self.xp // self.LEVEL_STEP + 1

    @property
    def learned_ids(self):
        return {sid for sid, m in self.mastery.items() if m.get("streak", 0) >= 2}

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
# Top-level manager used by the game
# --------------------------------------------------------------------------
class ChallengeManager:
    def __init__(
        self,
        words: List[VocabWord],
        rules: List[GrammarRule],
        progress_path: Optional[Path] = None,
        speech_available: bool = True,
        match_threshold: float = 0.6,
        xp_per_correct: int = 10,
    ):
        self.words = words
        self.rules = rules
        self.factory = ChallengeFactory(words, speech_available=speech_available)
        self.progress = Progress(progress_path)
        self.match_threshold = match_threshold
        self.xp_per_correct = xp_per_correct
        self._last_source: Optional[str] = None

    # -- selection ---------------------------------------------------------
    def next_challenge(self) -> Optional[Challenge]:
        # Mix vocabulary and grammar. ~70% vocab, 30% grammar when both exist.
        use_grammar = self.rules and (not self.words or random.random() < 0.3)
        if use_grammar:
            rule = self._weighted_pick(self.rules)
            self._last_source = rule.id
            return self.factory.build_grammar_fill(rule)
        if not self.words:
            return None
        word = self._weighted_pick(self.words)
        self._last_source = word.id
        return self.factory.for_word(word)

    def _weighted_pick(self, items):
        weights = []
        for it in items:
            w = self.progress.weight(it.id)
            if it.id == self._last_source:
                w *= 0.25  # avoid immediate repeats
            weights.append(w)
        return random.choices(items, weights=weights, k=1)[0]

    # -- grading -----------------------------------------------------------
    def grade(self, challenge: Challenge, given: str) -> ChallengeResult:
        given = (given or "").strip()
        if challenge.accepts_speech:
            correct = text_match(given, challenge.answer, self.match_threshold)
        else:
            correct = normalize(given) == normalize(challenge.answer)
        xp = self.xp_per_correct if correct else 0
        self.progress.record(challenge.source_id, correct, xp)
        detail = f'Heard: "{given}"' if challenge.accepts_speech and given else ""
        return ChallengeResult(
            correct=correct,
            given=given,
            expected=challenge.answer,
            explanation=challenge.explanation,
            xp=xp,
            detail=detail,
        )

    # -- helpers for the HUD ----------------------------------------------
    def stats(self) -> Dict[str, int]:
        return {
            "xp": self.progress.xp,
            "level": self.progress.level,
            "learned": len(self.progress.learned_ids),
            "total_words": len(self.words),
            "streak": self.progress.streak,
            "best_streak": self.progress.best_streak,
            "accuracy": int(
                100 * self.progress.total_correct / self.progress.total_attempts
            )
            if self.progress.total_attempts
            else 0,
        }

    def learned_words(self) -> List[VocabWord]:
        ids = self.progress.learned_ids
        return [w for w in self.words if w.id in ids]

    def prewarm_texts(self) -> List[str]:
        """Every phrase the narrator might speak -- used to pre-cache TTS."""
        texts = []
        for w in self.words:
            texts += [w.word, w.definition, w.example]
        for r in self.rules:
            texts.append(r.spoken or r.prompt.replace("___", r.answer))
        return [t for t in dict.fromkeys(texts) if t]
