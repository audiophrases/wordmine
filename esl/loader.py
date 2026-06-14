"""
Loads vocabulary JSON into typed models.

This is the single seam where external data enters the game. To plug in your
own content, point config.VOCAB_FILES at your files (or add more to the list --
they are merged). Malformed entries are skipped with a warning rather than
crashing the game.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .models import VocabWord


def _read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"[loader] data file not found, skipping: {path}")
    except json.JSONDecodeError as e:
        print(f"[loader] invalid JSON in {path}: {e}")
    return None


def load_vocabulary(paths: Iterable[Path]) -> List[VocabWord]:
    words: List[VocabWord] = []
    seen = set()
    for path in paths:
        data = _read_json(path)
        if not data:
            continue
        for raw in data.get("words", []):
            try:
                word = str(raw["word"]).strip()
                if not word:
                    continue
                wid = str(raw.get("id") or word)
                if wid in seen:
                    continue
                seen.add(wid)
                words.append(
                    VocabWord(
                        id=wid,
                        word=word,
                        definition=str(raw.get("definition", "")).strip(),
                        example=str(raw.get("example", "")).strip(),
                        phonetic=str(raw.get("phonetic", "")).strip(),
                        part_of_speech=str(raw.get("part_of_speech", "")).strip(),
                        category=str(raw.get("category", "general")).strip() or "general",
                        distractors=[str(d).strip() for d in raw.get("distractors", []) if str(d).strip()],
                        level=int(raw.get("level", 1)),
                        world_object=raw.get("world_object"),
                    )
                )
            except (KeyError, TypeError, ValueError) as e:
                print(f"[loader] skipping bad vocab entry {raw!r}: {e}")
    print(f"[loader] loaded {len(words)} vocabulary words")
    return words
