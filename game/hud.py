"""
Heads-up display: crosshair, hotbar, learner stats, narration subtitles,
transient toasts, and a toggleable Word Journal of learned vocabulary.

All elements are parented to camera.ui. Timers are advanced from HUD.update(),
called once per frame by the game loop.
"""
from __future__ import annotations

from typing import List

from ursina import Entity, Text, camera, color, window

from . import blocks


class HUD:
    def __init__(self):
        # Crosshair
        self.crosshair = Text(
            "+", parent=camera.ui, origin=(0, 0), position=(0, 0),
            scale=1.5, color=color.rgba(1, 1, 1, 0.7),
        )

        # Stats panel (top-left)
        self.stats_text = Text(
            "", parent=camera.ui, origin=(-0.5, 0.5),
            position=window.top_left + (0.02, -0.02),
            scale=0.9, color=color.white,
        )

        # Controls hint (top-right)
        self.controls = Text(
            "WASD move · Space jump · Mouse look\n"
            "L-click mine · R-click place · Scroll/1-6 select\n"
            "J journal · ESC release mouse",
            parent=camera.ui, origin=(0.5, 0.5),
            position=window.top_right + (-0.02, -0.02),
            scale=0.7, color=color.rgba(1, 1, 1, 0.75),
        )

        # Subtitle (narration captions) just above the hotbar
        self.subtitle = Text(
            "", parent=camera.ui, origin=(0, 0), position=(0, -0.34),
            scale=1.0, color=color.rgba(1, 1, 0.6, 1),
        )
        self._subtitle_timer = 0.0

        # Toast (transient feedback) near center
        self.toast_text = Text(
            "", parent=camera.ui, origin=(0, 0), position=(0, 0.28),
            scale=1.3, color=color.azure,
        )
        self._toast_timer = 0.0

        # Hotbar
        self.slot_size = 0.07
        self.slot_gap = 0.012
        self._slots: List[dict] = []
        self._build_hotbar(blocks.HOTBAR)

        # Word Journal (hidden until toggled)
        self.journal_bg = Entity(
            parent=camera.ui, model="quad", color=color.rgba(0, 0, 0, 0.85),
            scale=(0.9, 0.85), position=(0, 0), enabled=False,
        )
        self.journal_text = Text(
            "", parent=self.journal_bg, origin=(0, 0.5),
            position=(0, 0.46), scale=(1.0, 1.0), color=color.white,
        )
        self.journal_open = False

    # -- hotbar ------------------------------------------------------------
    def _build_hotbar(self, slot_blocks):
        n = len(slot_blocks)
        step = self.slot_size + self.slot_gap
        start_x = -(n - 1) / 2 * step
        y = window.bottom[1] + 0.06
        for i, bt in enumerate(slot_blocks):
            x = start_x + i * step
            bg = Entity(
                parent=camera.ui, model="quad",
                color=color.rgba(0, 0, 0, 0.5),
                scale=self.slot_size, position=(x, y, 0),
            )
            swatch = Entity(
                parent=camera.ui, model="quad", color=bt.color,
                scale=self.slot_size * 0.72, position=(x, y, -0.01),
            )
            key_label = Text(
                str(i + 1), parent=camera.ui, origin=(-0.5, -0.5),
                position=(x - self.slot_size / 2 + 0.004, y - self.slot_size / 2 + 0.004),
                scale=0.6, color=color.rgba(1, 1, 1, 0.8),
            )
            count_label = Text(
                "", parent=camera.ui, origin=(0.5, 0.5),
                position=(x + self.slot_size / 2 - 0.004, y + self.slot_size / 2 - 0.004),
                scale=0.7, color=color.white,
            )
            self._slots.append(
                {"bg": bg, "swatch": swatch, "count": count_label, "block": bt}
            )

    def update_hotbar(self, inventory):
        for i, slot in enumerate(self._slots):
            bid = slot["block"].id
            slot["count"].text = str(inventory.count(bid))
            selected = i == inventory.selected_index
            slot["bg"].color = color.rgba(1, 1, 1, 0.45) if selected else color.rgba(0, 0, 0, 0.5)
            slot["bg"].scale = self.slot_size * (1.12 if selected else 1.0)

    # -- text feedback -----------------------------------------------------
    def set_stats(self, s: dict):
        self.stats_text.text = (
            f"<azure>WordMine\n"
            f"<white>Level {s['level']}   XP {s['xp']}\n"
            f"Words learned {s['learned']}/{s['total_words']}\n"
            f"Streak {s['streak']} (best {s['best_streak']})   Acc {s['accuracy']}%"
        )

    def toast(self, message: str, duration: float = 2.5, col=None):
        self.toast_text.text = message
        self.toast_text.color = col or color.azure
        self._toast_timer = duration

    def show_subtitle(self, message: str, duration: float = 3.0):
        self.subtitle.text = message
        self._subtitle_timer = duration

    def update(self, dt: float):
        if self._toast_timer > 0:
            self._toast_timer -= dt
            if self._toast_timer <= 0:
                self.toast_text.text = ""
        if self._subtitle_timer > 0:
            self._subtitle_timer -= dt
            if self._subtitle_timer <= 0:
                self.subtitle.text = ""

    # -- journal -----------------------------------------------------------
    def toggle_journal(self, learned_words, total: int):
        self.journal_open = not self.journal_open
        self.journal_bg.enabled = self.journal_open
        if self.journal_open:
            lines = [f"<azure>WORD JOURNAL  ({len(learned_words)}/{total} learned)<white>", ""]
            if not learned_words:
                lines.append("Mine glowing Word Ore and answer correctly")
                lines.append("twice to add words here.")
            for w in learned_words:
                lines.append(f"<gold>{w.word}<white>  {w.phonetic}")
                lines.append(f"   {w.definition}")
            self.journal_text.text = "\n".join(lines)
        return self.journal_open
