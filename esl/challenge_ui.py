"""
Modal challenge overlay (Ursina).

Renders a Challenge, plays its narration through the TTS engine, accepts the
answer (number keys for choices, push-to-talk [V] for speaking), grades it via
the ChallengeManager, and shows feedback.

Threading note: speech transcription finishes on a worker thread. Rather than
touch the Panda3D scene graph from there (unsafe), the callback stashes the
result and `update()` (main thread) picks it up next frame.
"""
from __future__ import annotations

from typing import Callable, Optional

from ursina import Entity, Text, camera, color

from .models import Challenge, ChallengeResult


class ChallengeUI:
    def __init__(self, tts, speech, on_result: Callable, on_close: Callable):
        self.tts = tts
        self.speech = speech
        self.on_result = on_result   # (challenge, result) -> game side effects
        self.on_close = on_close     # () -> resume gameplay

        self.active = False
        self.phase = "idle"          # answer | recording | thinking | feedback
        self.manager = None
        self.challenge: Optional[Challenge] = None
        self._pending_speech = None  # set by speech worker thread

        self._build()

    def _build(self):
        self.root = Entity(parent=camera.ui, enabled=False)
        # dim the world behind the modal
        Entity(parent=self.root, model="quad", color=color.rgba(0, 0, 0, 0.82),
               scale=(2, 1), z=0.1)
        self.panel = Entity(parent=self.root, model="quad",
                            color=color.rgba(0.10, 0.12, 0.18, 0.98),
                            scale=(0.88, 0.80))
        self.title = Text(parent=self.root, origin=(0, 0), position=(0, 0.31),
                          scale=1.7, color=color.gold)
        # NOTE: Ursina's Text only creates `raw_text` when given non-empty text,
        # and the `wordwrap` setter needs it -- so seed these with a placeholder.
        self.instruction = Text(" ", parent=self.root, origin=(0, 0), position=(0, 0.22),
                                scale=0.9, color=color.rgba(1, 1, 1, 0.85),
                                wordwrap=60)
        self.prompt = Text(" ", parent=self.root, origin=(0, 0.5), position=(0, 0.13),
                           scale=1.25, color=color.white, wordwrap=42)
        self.options = Text(parent=self.root, origin=(-0.5, 0.5),
                            position=(-0.30, -0.06), scale=1.15, color=color.azure)
        self.feedback = Text(" ", parent=self.root, origin=(0, 0.5), position=(0, -0.20),
                             scale=0.95, color=color.white, wordwrap=58)
        self.footer = Text(parent=self.root, origin=(0, 0), position=(0, -0.35),
                           scale=0.75, color=color.rgba(1, 1, 1, 0.7))

    # -- lifecycle ---------------------------------------------------------
    def open(self, challenge: Challenge, manager):
        self.challenge = challenge
        self.manager = manager
        self.active = True
        self.phase = "answer"
        self.root.enabled = True
        self._pending_speech = None

        self.title.text = challenge.title
        self.instruction.text = challenge.instruction
        self.prompt.text = "(  Listen carefully . . .  )" if challenge.hide_prompt_text else challenge.prompt_text

        if challenge.options:
            self.options.text = "\n\n".join(
                f"[{i + 1}]   {opt}" for i, opt in enumerate(challenge.options)
            )
        else:
            self.options.text = ""

        self.feedback.text = ""
        self._update_footer()

        if challenge.spoken_text:
            self.tts.speak(challenge.spoken_text)

    def close(self):
        self.active = False
        self.phase = "idle"
        self.root.enabled = False
        self.tts.stop()
        self.on_close()

    # -- input -------------------------------------------------------------
    def input(self, key: str):
        """Consume all input while the modal is open."""
        if not self.active:
            return
        ch = self.challenge

        if self.phase == "feedback":
            if key in ("enter", "space", "left mouse down"):
                self.close()
            return

        if self.phase == "recording":
            if key == "v up":
                self._stop_recording()
            return

        if self.phase == "thinking":
            return

        # phase == "answer"
        if key == "r" and ch.spoken_text:
            self.tts.speak(ch.spoken_text)
            return

        if ch.accepts_speech:
            if key == "v" and self.speech.available:
                self._start_recording()
            elif key == "enter":
                # skip / fallback when mic isn't set up
                self._skip_speaking()
            return

        # choice-based answer
        if key in ("1", "2", "3", "4", "5", "6"):
            idx = int(key) - 1
            if idx < len(ch.options):
                self._answer(ch.options[idx])

    # -- speaking flow -----------------------------------------------------
    def _start_recording(self):
        self.tts.stop()
        if self.speech.begin():
            self.phase = "recording"
            self.feedback.text = "<azure>Recording . . .  release [V] when finished"
            self._update_footer()
        else:
            self.feedback.text = "<red>Microphone unavailable."

    def _stop_recording(self):
        self.phase = "thinking"
        self.feedback.text = "Recognizing your speech . . ."
        self._update_footer()
        self._pending_speech = None
        self.speech.end_async(lambda text: setattr(self, "_pending_speech", (text,)))

    def _skip_speaking(self):
        result = ChallengeResult(
            correct=False, given="", expected=self.challenge.answer,
            explanation=self.challenge.explanation, xp=0,
            detail="Skipped (run setup_models.py to enable the microphone).",
        )
        self._show_result(result)

    # -- choice flow -------------------------------------------------------
    def _answer(self, choice: str):
        result = self.manager.grade(self.challenge, choice)
        self._show_result(result)

    # -- shared ------------------------------------------------------------
    def _show_result(self, result: ChallengeResult):
        self.phase = "feedback"
        # reveal hidden prompt text (e.g. the definition behind a listening task)
        if self.challenge.hide_prompt_text:
            self.prompt.text = self.challenge.prompt_text

        if result.correct:
            head = "<lime>Correct!"
            if result.xp:
                head += f"   +{result.xp} XP"
        else:
            head = f"<red>Not quite.   Answer:  <white>{result.expected}"

        parts = [head]
        if result.detail:
            parts.append(f"<azure>{result.detail}")
        if result.explanation:
            parts.append(f"<white>{result.explanation}")
        self.feedback.text = "\n".join(parts)
        self.options.text = ""

        reveal = self.challenge.meta.get("reveal_spoken")
        if reveal:
            self.tts.speak(reveal)

        self._update_footer()
        self.on_result(self.challenge, result)

    def _update_footer(self):
        ch = self.challenge
        if self.phase == "feedback":
            self.footer.text = "[Enter] continue"
        elif self.phase == "recording":
            self.footer.text = "release [V] to submit"
        elif self.phase == "thinking":
            self.footer.text = "recognizing your speech . . ."
        elif ch and ch.accepts_speech:
            if self.speech.available:
                self.footer.text = "hold [V] and speak   ·   [R] replay   ·   [Enter] skip"
            else:
                self.footer.text = "[Enter] continue   (mic not set up — run setup_models.py)"
        else:
            n = len(ch.options) if ch else 0
            self.footer.text = f"press [1]-[{n}] to answer   ·   [R] replay audio"

    # -- per-frame ---------------------------------------------------------
    def update(self):
        if self.phase == "thinking" and self._pending_speech is not None:
            heard = self._pending_speech[0]
            self._pending_speech = None
            result = self.manager.grade(self.challenge, heard)
            self._show_result(result)
