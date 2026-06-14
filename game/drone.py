"""
Companion Drone -- a small floating orb that flies to whatever the player is
looking at, glows, and acts as the "voice" of the game (it lights up when a word
is spoken, listens when you hold the mic, and flashes green/red on the result).

It is the only on-screen guidance: no text, just motion, colour and light.
"""
from __future__ import annotations

import math

from ursina import Entity, Vec3, color, lerp, time


# state colours
_IDLE = color.rgba(0.55, 0.8, 1.0, 1)
_SPEAK = color.rgba(1.0, 0.85, 0.3, 1)
_LISTEN = color.rgba(0.2, 1.0, 1.0, 1)
_GOOD = color.rgba(0.3, 1.0, 0.4, 1)
_BAD = color.rgba(1.0, 0.35, 0.35, 1)


class CompanionDrone:
    def __init__(self):
        self.root = Entity()
        self.core = Entity(parent=self.root, model="sphere", scale=0.32,
                           color=_IDLE, unlit=True)
        self.halo = Entity(parent=self.root, model="sphere", scale=0.55,
                           color=color.rgba(0.55, 0.8, 1.0, 0.25), unlit=True,
                           double_sided=True)
        # little orbiting accent so it reads as a drone, not just a ball
        self.ring = Entity(parent=self.root, model="cube", scale=(0.7, 0.05, 0.05),
                           color=color.rgba(1, 1, 1, 0.6), unlit=True)
        self.base_color = _IDLE
        self._flash_t = 0.0
        self._flash_color = _IDLE
        self.root.position = (0, 3, 0)

    # -- state ------------------------------------------------------------
    def set_idle(self):
        self.base_color = _IDLE

    def set_speaking(self):
        self.base_color = _SPEAK

    def set_listening(self):
        self.base_color = _LISTEN

    def flash_good(self):
        self._flash(_GOOD)

    def flash_bad(self):
        self._flash(_BAD)

    def _flash(self, c):
        self._flash_t = 0.6
        self._flash_color = c

    # -- per-frame --------------------------------------------------------
    def update(self, target_entity, player):
        dt = time.dt
        if target_entity is not None:
            top = getattr(target_entity, "drone_anchor", 1.2)
            desired = target_entity.world_position + Vec3(0, top + 0.6, 0)
        else:
            desired = (player.world_position
                       + player.forward * 2.1
                       + player.right * 1.15
                       + Vec3(0, 0.9, 0))
        desired += Vec3(0, math.sin(time.time() * 2.2) * 0.12, 0)
        self.root.world_position = lerp(self.root.world_position, desired, min(1, dt * 4))

        # spin the accent ring
        self.ring.rotation_y += dt * 220

        # colour (flash overrides base briefly)
        if self._flash_t > 0:
            self._flash_t -= dt
            c = self._flash_color
        else:
            c = self.base_color
        pulse = 0.85 + 0.15 * math.sin(time.time() * 6)
        self.core.color = color.rgba(c[0] * pulse, c[1] * pulse, c[2] * pulse, 1)
        self.halo.color = color.rgba(c[0], c[1], c[2], 0.22)
