"""
Minimal, text-free HUD for the audio-only experience.

Everything here is iconographic -- there is no readable English in the gameplay
loop. It provides: an aiming reticle that changes colour by state, a pulsing
"listening" ring while the mic is held, a boot-time loading bar (while TTS is
pre-baked), and a row of colour pips showing what you've collected.
"""
from __future__ import annotations

import math
import time as _time

from ursina import Entity, camera, color, window


_RETICLE = {
    "idle": color.rgba(1, 1, 1, 0.7),
    "target": color.rgba(1.0, 0.85, 0.2, 1),   # gold: "you can echo this"
    "listen": color.rgba(0.2, 1.0, 1.0, 1),    # cyan: recording
}


class HUD:
    def __init__(self):
        # aiming reticle (a small dot)
        self.reticle = Entity(parent=camera.ui, model="circle", scale=0.009,
                              color=_RETICLE["idle"])
        # pulsing listening ring (hidden until recording)
        self.ring = Entity(parent=camera.ui, model="circle",
                           scale=0.05, color=color.rgba(0.2, 1, 1, 0.0),
                           double_sided=True)
        self._listening = False

        # boot loading bar
        self.loading_root = Entity(parent=camera.ui)
        Entity(parent=self.loading_root, model="quad", scale=(0.54, 0.06),
               color=color.rgba(0, 0, 0, 0.65))
        self.load_fill = Entity(parent=self.loading_root, model="quad",
                                origin=(-0.5, 0), position=(-0.25, 0, -0.02),
                                scale=(0.0001, 0.04), color=color.azure)
        self.load_dot = Entity(parent=self.loading_root, model="circle",
                               position=(0, 0.07, -0.02), scale=0.02, color=color.cyan)

        # Calm full-screen overlays are kept transparent in the current
        # listen/action mode; these can be reused for future hint or comfort tints.
        self.vignette = Entity(parent=camera.ui, model="quad", scale=(2.2, 1.2),
                               z=1.0, color=color.rgba(1, 0, 0, 0))
        self.hidden_ov = Entity(parent=camera.ui, model="quad", scale=(2.2, 1.2),
                                z=1.0, color=color.rgba(0.15, 0.4, 0.7, 0))
        self._danger = 0.0

        # collection pips (bottom-centre)
        self._pips = []
        self._pip_y = window.bottom[1] + 0.04

    # -- loading -----------------------------------------------------------
    def set_loading(self, frac: float):
        self.load_fill.scale_x = max(0.0001, 0.5 * min(1.0, max(0.0, frac)))

    def finish_loading(self):
        self.loading_root.enabled = False

    # -- reticle / mic -----------------------------------------------------
    def set_reticle(self, state: str):
        self.reticle.color = _RETICLE.get(state, _RETICLE["idle"])

    def set_listening(self, on: bool):
        self._listening = on
        if not on:
            self.ring.color = color.rgba(0.2, 1, 1, 0.0)

    # -- threat / hidden feedback -----------------------------------------
    def set_danger(self, frac: float):
        self._danger = max(0.0, min(1.0, frac))

    def set_hidden(self, on: bool):
        self.hidden_ov.color = color.rgba(0.15, 0.4, 0.7, 0.22 if on else 0.0)

    # -- collection feedback ----------------------------------------------
    def add_pip(self, col):
        pip = Entity(parent=camera.ui, model="quad", scale=0.028,
                     color=col, position=(0, self._pip_y, 0))
        self._pips.append(pip)
        step = 0.036
        start = -(len(self._pips) - 1) / 2 * step
        for i, p in enumerate(self._pips):
            p.x = start + i * step

    def clear_pips(self):
        for p in self._pips:
            from ursina import destroy
            destroy(p)
        self._pips = []

    # -- per-frame ---------------------------------------------------------
    def update(self, dt: float):
        if self.loading_root.enabled:
            self.load_dot.x = math.sin(_time.perf_counter() * 4) * 0.24
        t = _time.perf_counter()
        if self._listening:
            pulse = 0.045 + 0.015 * math.sin(t * 10)
            self.ring.scale = pulse
            self.ring.color = color.rgba(0.2, 1, 1, 0.5 + 0.3 * math.sin(t * 10))
        # danger vignette pulses faster as it intensifies
        if self._danger > 0.01:
            beat = 0.8 + 0.2 * math.sin(t * (4 + 8 * self._danger))
            self.vignette.color = color.rgba(1, 0, 0, self._danger * 0.5 * beat)
        else:
            self.vignette.color = color.rgba(1, 0, 0, 0)
