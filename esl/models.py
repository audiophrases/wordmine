"""
Data models for the ESL layer.

Kept framework-agnostic (no Ursina imports) so the learning logic can be tested
or reused outside the game.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    # optional visual representation in the 3D world (See-Echo-Act props):
    #   {"shape": "...", "color": [r,g,b], "scale": n, "count": n}
    world_object: Optional[Dict[str, Any]] = None
