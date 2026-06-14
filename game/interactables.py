"""
Interactables for the heist's "See · Hear · Echo · Act" loop.

An Interactable bundles a 3D prop, the English word the player must *say* to act
on it, and a `kind` that main.py maps to an effect (collect, open, close, stop,
hide, run, gate). Props are built from many small primitives for a more natural,
recognisable low-poly look (a key looks like a key, a dog like a dog).
"""
from __future__ import annotations

import math
from typing import Callable, Optional, Tuple

from ursina import Entity, color, time

from esl.models import VocabWord


def _color(rgb, default=(0.8, 0.8, 0.8)):
    try:
        return color.rgb(float(rgb[0]), float(rgb[1]), float(rgb[2]))
    except Exception:  # noqa: BLE001
        return color.rgb(*default)


def _darker(c, k=0.55):
    return color.rgb(c[0] * k, c[1] * k, c[2] * k)


# --------------------------------------------------------------------------
# Procedural prop builders.  Each attaches detailed visuals to `root` (base on
# the ground at root.y) and returns the bounding box (w, h, d) for the collider.
# --------------------------------------------------------------------------
def _b_key(root, c, s):
    s *= 0.38
    Entity(parent=root, model="sphere", color=c, position=(0, 0.92 * s, 0),
           scale=(0.55 * s, 0.55 * s, 0.13 * s))                      # ring head
    Entity(parent=root, model="sphere", color=_darker(c, 0.4), position=(0, 0.92 * s, 0.02),
           scale=(0.26 * s, 0.26 * s, 0.16 * s))                      # ring hole
    Entity(parent=root, model="cube", color=c, position=(0, 0.42 * s, 0),
           scale=(0.12 * s, 0.85 * s, 0.12 * s))                      # shaft
    Entity(parent=root, model="cube", color=c, position=(0.12 * s, 0.18 * s, 0),
           scale=(0.14 * s, 0.10 * s, 0.12 * s))                      # tooth
    Entity(parent=root, model="cube", color=c, position=(0.12 * s, 0.34 * s, 0),
           scale=(0.10 * s, 0.10 * s, 0.12 * s))                      # tooth
    return (0.55 * s, 1.05 * s, 0.25 * s)


def _b_tool(root, c, s):
    s *= 0.42
    Entity(parent=root, model="cube", color=c, position=(0, 0.5 * s, 0),
           scale=(0.15 * s, 1.0 * s, 0.15 * s))                       # handle
    Entity(parent=root, model="cube", color=c, position=(0, 1.02 * s, 0),
           scale=(0.5 * s, 0.18 * s, 0.18 * s))                       # head
    Entity(parent=root, model="cube", color=_darker(c, 0.7), position=(0.2 * s, 1.13 * s, 0),
           scale=(0.14 * s, 0.26 * s, 0.2 * s))                       # open jaw
    return (0.55 * s, 1.2 * s, 0.22 * s)


def _b_battery(root, c, s):
    s *= 0.42
    Entity(parent=root, model="cube", color=c, position=(0, 0.5 * s, 0),
           scale=(0.5 * s, 1.0 * s, 0.5 * s))                         # body
    Entity(parent=root, model="cube", color=color.rgb(0.85, 0.8, 0.2),
           position=(0, 1.05 * s, 0), scale=(0.2 * s, 0.12 * s, 0.2 * s))  # + terminal
    Entity(parent=root, model="cube", color=color.rgb(0.96, 0.96, 0.96),
           position=(0, 0.72 * s, 0.255 * s), scale=(0.5 * s, 0.2 * s, 0.02 * s))  # label
    return (0.55 * s, 1.1 * s, 0.55 * s)


def _b_dog(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.42 * s, 0),
           scale=(0.72 * s, 0.32 * s, 0.34 * s))                      # body
    Entity(parent=root, model="cube", color=c, position=(0.42 * s, 0.58 * s, 0),
           scale=(0.3 * s, 0.3 * s, 0.3 * s))                         # head
    Entity(parent=root, model="cube", color=c, position=(0.6 * s, 0.52 * s, 0),
           scale=(0.18 * s, 0.16 * s, 0.18 * s))                      # snout
    for ez in (-0.1, 0.1):
        Entity(parent=root, model="cube", color=_darker(c, 0.8),
               position=(0.38 * s, 0.74 * s, ez * s), scale=(0.08 * s, 0.14 * s, 0.08 * s))  # ears
    Entity(parent=root, model="cube", color=c, position=(-0.42 * s, 0.55 * s, 0),
           scale=(0.22 * s, 0.07 * s, 0.07 * s))                      # tail
    for dx in (-0.26, 0.26):
        for dz in (-0.12, 0.12):
            Entity(parent=root, model="cube", color=_darker(c, 0.85),
                   position=(dx * s, 0.14 * s, dz * s), scale=(0.1 * s, 0.28 * s, 0.1 * s))  # legs
    return (1.0 * s, 0.78 * s, 0.36 * s)


def _b_house(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 1.1 * s, 0),
           scale=(2.6 * s, 2.2 * s, 2.6 * s))                         # walls
    Entity(parent=root, model="cube", color=_darker(c, 0.6), position=(0, 2.45 * s, 0),
           scale=(3.0 * s, 0.5 * s, 3.0 * s))                         # roof
    Entity(parent=root, model="cube", color=color.rgb(0.12, 0.1, 0.1),
           position=(0, 0.85 * s, 1.32 * s), scale=(0.9 * s, 1.5 * s, 0.12 * s))  # doorway
    return (3.0 * s, 2.7 * s, 3.0 * s)


def _b_shadow(root, c, s):
    disc = Entity(parent=root, model="circle", color=color.rgba(0, 0, 0, 0.55),
                  position=(0, 0.03, 0), scale=1.7 * s, unlit=True)
    disc.rotation_x = 90
    return (1.7 * s, 0.25, 1.7 * s)


def _b_sphere(root, c, s):
    Entity(parent=root, model="sphere", color=c, position=(0, 0.5 * s, 0), scale=s)
    return (s, s, s)


BUILDERS = {
    "key": _b_key, "tool": _b_tool, "battery": _b_battery, "dog": _b_dog,
    "house": _b_house, "shadow": _b_shadow, "sphere": _b_sphere,
}


# --------------------------------------------------------------------------
# Interactable
# --------------------------------------------------------------------------
class Interactable:
    def __init__(
        self,
        anchor: Entity,
        kind: str,
        word: Optional[VocabWord] = None,
        word_provider: Optional[Callable[[], VocabWord]] = None,
        collider_entity: Optional[Entity] = None,
        height: float = 1.0,
        repeatable: bool = False,
        cooldown: float = 0.0,
        payload: Optional[dict] = None,
    ):
        self.root = anchor
        self.kind = kind
        self._word = word
        self._word_provider = word_provider
        self.height = height
        self.repeatable = repeatable
        self.cooldown = cooldown
        self._cd = 0.0
        self.payload = payload or {}
        self.done = False
        self.marker: Optional[Entity] = None
        anchor.drone_anchor = height
        (collider_entity or anchor).interactable = self

    def current_word(self) -> Optional[VocabWord]:
        if self._word is None and self._word_provider is not None:
            self._word = self._word_provider()
        return self._word

    def available(self) -> bool:
        return (not self.done) and self._cd <= 0

    def tick(self, dt: float):
        if self._cd > 0:
            self._cd -= dt

    def set_highlight(self, on: bool):
        if on and self.marker is None:
            self.marker = Entity(parent=self.root, model="cube", color=color.gold,
                                 unlit=True, position=(0, self.height + 0.7, 0),
                                 scale=0.22, rotation=(45, 45, 0))
        if self.marker:
            self.marker.enabled = on and self.available()

    def animate_marker(self):
        if self.marker and self.marker.enabled:
            self.marker.rotation_y += time.dt * 120
            self.marker.y = self.height + 0.7 + math.sin(time.time() * 3) * 0.1

    def succeed(self):
        if self.repeatable:
            self._cd = self.cooldown
        else:
            self.done = True
        if self.marker:
            self.marker.enabled = False


# --------------------------------------------------------------------------
# Build a prop from a word's spec (used for scavenge items & hide spots)
# --------------------------------------------------------------------------
def build_object(word: VocabWord, position, kind: str, **kwargs) -> Interactable:
    spec = word.world_object or {}
    shape = kwargs.pop("shape", spec.get("shape", "sphere"))
    c = _color(kwargs.pop("color", spec.get("color", [0.8, 0.8, 0.8])))
    s = float(kwargs.pop("scale", spec.get("scale", 1.0)))
    root = Entity(position=position)
    w, h, d = BUILDERS.get(shape, _b_sphere)(root, c, s)
    col = Entity(parent=root, model="cube", position=(0, h / 2, 0),
                 scale=(w, h, d), visible=False, collider="box")
    return Interactable(root, kind, word=word, height=h, collider_entity=col, **kwargs)


def build_decor(shape: str, position, rgb, scale=1.0) -> Entity:
    """A non-interactive scenery prop (no word, no echo)."""
    root = Entity(position=position)
    BUILDERS.get(shape, _b_sphere)(root, _color(rgb), float(scale))
    return root
