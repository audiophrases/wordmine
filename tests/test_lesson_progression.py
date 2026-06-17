"""Regression checks for WordMine's room-vs-level progression.

Run from the repository root with:
    python tests/test_lesson_progression.py
"""
from __future__ import annotations

import ast
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _main_tree():
    return ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))


def _literal_from_main(name: str):
    for node in _main_tree().body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in main.py")


def _main_names():
    names = set()
    for node in _main_tree().body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _vocab_ids():
    data = json.loads((ROOT / "data" / "vocabulary.json").read_text(encoding="utf-8"))
    return {word["id"] for word in data["words"]}


def _class_method_names(class_name: str):
    names = set()
    for node in _main_tree().body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    names.add(item.name)
    return names


def test_room_transitions_are_manual_go_to_next_room_prompts():
    prompts = _literal_from_main("LEVEL_PROMPTS")
    level_one_phrases = [prompt["phrase"] for prompt in prompts[1]]
    level_one_targets = [prompt["target"] for prompt in prompts[1]]

    assert "AUTO_OPEN_GATES_AFTER_PROMPTS" not in _main_names()
    assert level_one_phrases[4] == "Go to the next room."
    assert level_one_targets[4] == "open"
    assert level_one_phrases[9] == "Go to the next room."
    assert level_one_targets[9] == "open"
    assert "Open the blue door." not in level_one_phrases
    assert "Open the green door." not in level_one_phrases
    assert "Look at the door." not in level_one_phrases


def test_level_one_has_a_manual_next_level_transition_and_level_two_exists():
    prompts = _literal_from_main("LEVEL_PROMPTS")
    level_one_phrases = [prompt["phrase"] for prompt in prompts[1]]
    level_one_targets = [prompt["target"] for prompt in prompts[1]]
    level_two_phrases = [prompt["phrase"] for prompt in prompts[2]]

    assert level_one_phrases[-1] == "Go to the next level."
    assert level_one_targets[-1] == "open"
    assert len(level_two_phrases) >= 8
    assert level_two_phrases[:4] == ["Banana.", "Chair.", "Shoe.", "Car."]
    assert "Touch the car." in level_two_phrases


def test_level_two_teaches_color_and_size_apple_vocabulary():
    prompts = _literal_from_main("LEVEL_PROMPTS")
    level_two = prompts[2]
    level_two_phrases = [prompt["phrase"] for prompt in level_two]
    level_two_targets = {prompt["target"] for prompt in level_two}
    vocab_ids = _vocab_ids()

    for word_id, phrase in {
        "red_apple": "Red apple.",
        "green_apple": "Green apple.",
        "big_apple": "Big apple.",
        "small_apple": "Small apple.",
    }.items():
        assert word_id in vocab_ids
        assert word_id in level_two_targets
        assert phrase in level_two_phrases


def test_level_two_has_grab_and_place_prompts():
    prompts = _literal_from_main("LEVEL_PROMPTS")
    place_prompts = [prompt for prompt in prompts[2] if prompt.get("action") == "place"]

    assert place_prompts == [
        {
            "phrase": "Put the red apple in the basket.",
            "action": "place",
            "target": "red_apple",
            "destination": "basket",
        },
        {
            "phrase": "Put the green apple on the table.",
            "action": "place",
            "target": "green_apple",
            "destination": "table",
        },
        {
            "phrase": "Put the big apple in the box.",
            "action": "place",
            "target": "big_apple",
            "destination": "box",
        },
        {
            "phrase": "Put the small apple on the chair.",
            "action": "place",
            "target": "small_apple",
            "destination": "chair",
        },
    ]
    assert {"_handle_place_prompt", "_pick_up", "_place_carried"} <= _class_method_names("WordMine")


if __name__ == "__main__":
    test_room_transitions_are_manual_go_to_next_room_prompts()
    test_level_one_has_a_manual_next_level_transition_and_level_two_exists()
    test_level_two_teaches_color_and_size_apple_vocabulary()
    test_level_two_has_grab_and_place_prompts()
    print("lesson progression tests ok")
