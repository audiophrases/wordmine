"""
Data models for the ESL engine.

These are deliberately framework-agnostic (no Ursina imports) so the whole
learning layer can be unit-tested or reused outside the game.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

# Challenge type identifiers. Add a new one here, register a builder in
# engine.ChallengeFactory, and render it in challenge_ui -- nothing else needs
# to change.
LISTEN_AND_CHOOSE = "listen_and_choose"   # hear a definition, pick the word
DEFINITION_MATCH = "definition_match"     # read a definition, pick the word
SPEAK_THE_WORD = "speak_the_word"         # say the word into the mic
GRAMMAR_FILL = "grammar_fill"             # choose the correct word for a blank

ALL_TYPES = (LISTEN_AND_CHOOSE, DEFINITION_MATCH, SPEAK_THE_WORD, GRAMMAR_FILL)


@dataclass
class VocabWord:
    """One vocabulary entry loaded from JSON."""
    id: str
    word: str
    definition: str = ""
    example: str = ""
    phonetic: str = ""
    part_of_speech: str = ""
    category: str = "general"
    distractors: List[str] = field(default_factory=list)
    level: int = 1


@dataclass
class GrammarRule:
    """One grammar fill-in-the-blank item loaded from JSON."""
    id: str
    topic: str
    prompt: str
    options: List[str]
    answer: str
    explanation: str = ""
    spoken: str = ""
    level: int = 1


@dataclass
class Challenge:
    """
    A single, self-contained question shown to the player.

    The UI only ever sees a Challenge, so the rest of the game does not care
    whether it came from a vocabulary word or a grammar rule.
    """
    type: str
    title: str                       # short banner, e.g. "Listen & Choose"
    instruction: str                 # what the player should do
    prompt_text: str                 # body text (may be hidden for listening)
    spoken_text: str                 # what the TTS narrator should say
    answer: str                      # correct option text OR target phrase
    options: List[str] = field(default_factory=list)
    explanation: str = ""            # shown after answering
    accepts_speech: bool = False     # answered by speaking into the mic
    hide_prompt_text: bool = False   # pure-listening: don't reveal the text
    source_id: str = ""              # id of the originating word/rule (for mastery)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChallengeResult:
    """Outcome of answering a challenge."""
    correct: bool
    given: str
    expected: str
    explanation: str = ""
    xp: int = 0
    detail: str = ""   # e.g. what the mic heard
