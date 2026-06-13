"""
Loads vocabulary and grammar JSON into typed models.

This is the single seam where external data enters the game. To plug in your
own content, point config.VOCAB_FILES / GRAMMAR_FILES at your files (or add
more to the list -- they are merged). Malformed entries are skipped with a
warning rather than crashing the game.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .models import GrammarRule, VocabWord


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
                    )
                )
            except (KeyError, TypeError, ValueError) as e:
                print(f"[loader] skipping bad vocab entry {raw!r}: {e}")
    print(f"[loader] loaded {len(words)} vocabulary words")
    return words


def load_grammar(paths: Iterable[Path]) -> List[GrammarRule]:
    rules: List[GrammarRule] = []
    seen = set()
    for path in paths:
        data = _read_json(path)
        if not data:
            continue
        for raw in data.get("rules", []):
            try:
                prompt = str(raw["prompt"]).strip()
                options = [str(o).strip() for o in raw["options"] if str(o).strip()]
                answer = str(raw["answer"]).strip()
                if not prompt or len(options) < 2 or answer not in options:
                    print(f"[loader] skipping invalid grammar rule: {raw.get('id', prompt)!r}")
                    continue
                rid = str(raw.get("id") or prompt)
                if rid in seen:
                    continue
                seen.add(rid)
                rules.append(
                    GrammarRule(
                        id=rid,
                        topic=str(raw.get("topic", "Grammar")).strip(),
                        prompt=prompt,
                        options=options,
                        answer=answer,
                        explanation=str(raw.get("explanation", "")).strip(),
                        spoken=str(raw.get("spoken", "")).strip(),
                        level=int(raw.get("level", 1)),
                    )
                )
            except (KeyError, TypeError, ValueError) as e:
                print(f"[loader] skipping bad grammar entry {raw!r}: {e}")
    print(f"[loader] loaded {len(rules)} grammar rules")
    return rules
