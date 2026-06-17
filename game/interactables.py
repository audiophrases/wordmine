"""
Interactables for the audio-first "Listen · Aim · Act" loop.

An Interactable bundles a 3D prop, the English word associated with it, and a
`kind` that main.py maps to calm lesson effects such as touch feedback or opening
a lesson gate. Props are built from many small primitives for a more natural,
recognisable low-poly look.
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


def _b_apple(root, c, s):
    Entity(parent=root, model="sphere", color=c, position=(0, 0.48 * s, 0), scale=(0.72 * s, 0.72 * s, 0.72 * s))
    Entity(parent=root, model="cube", color=color.rgb(0.35, 0.18, 0.08), position=(0, 0.92 * s, 0), scale=(0.08 * s, 0.26 * s, 0.08 * s))
    Entity(parent=root, model="cube", color=color.rgb(0.18, 0.55, 0.18), position=(0.16 * s, 0.98 * s, 0), scale=(0.26 * s, 0.08 * s, 0.14 * s), rotation=(0, 0, 20))
    return (0.85 * s, 1.1 * s, 0.85 * s)


def _b_cup(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.45 * s, 0), scale=(0.58 * s, 0.9 * s, 0.58 * s))
    Entity(parent=root, model="cube", color=color.rgb(0.96, 0.96, 0.9), position=(0, 0.92 * s, 0), scale=(0.48 * s, 0.08 * s, 0.48 * s))
    Entity(parent=root, model="cube", color=_darker(c, 0.8), position=(0.42 * s, 0.55 * s, 0), scale=(0.14 * s, 0.48 * s, 0.14 * s))
    return (0.75 * s, 1.0 * s, 0.65 * s)


def _b_ball(root, c, s):
    Entity(parent=root, model="sphere", color=c, position=(0, 0.5 * s, 0), scale=s)
    Entity(parent=root, model="cube", color=color.rgba(1, 1, 1, 0.45), position=(0, 0.5 * s, 0.51 * s), scale=(0.13 * s, 0.86 * s, 0.03 * s), unlit=True)
    return (s, s, s)


def _b_book(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.16 * s, 0), scale=(0.9 * s, 0.22 * s, 0.62 * s))
    Entity(parent=root, model="cube", color=color.rgb(0.96, 0.92, 0.78), position=(0.04 * s, 0.29 * s, 0), scale=(0.78 * s, 0.05 * s, 0.54 * s))
    Entity(parent=root, model="cube", color=_darker(c, 0.55), position=(-0.46 * s, 0.31 * s, 0), scale=(0.07 * s, 0.12 * s, 0.64 * s))
    return (1.0 * s, 0.42 * s, 0.72 * s)


def _b_box(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.45 * s, 0), scale=(0.9 * s, 0.9 * s, 0.9 * s))
    Entity(parent=root, model="cube", color=_darker(c, 0.55), position=(0, 0.92 * s, 0), scale=(0.96 * s, 0.08 * s, 0.96 * s))
    return (1.0 * s, 1.0 * s, 1.0 * s)


def _b_table(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.82 * s, 0), scale=(1.6 * s, 0.18 * s, 1.0 * s))
    for x in (-0.62, 0.62):
        for z in (-0.36, 0.36):
            Entity(parent=root, model="cube", color=_darker(c, 0.75), position=(x * s, 0.38 * s, z * s), scale=(0.14 * s, 0.76 * s, 0.14 * s))
    return (1.7 * s, 0.95 * s, 1.1 * s)


def _b_basket(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.3 * s, 0), scale=(1.0 * s, 0.6 * s, 0.8 * s))
    Entity(parent=root, model="cube", color=color.rgba(0.05, 0.04, 0.03, 0.35), position=(0, 0.66 * s, 0), scale=(0.82 * s, 0.08 * s, 0.62 * s), unlit=True)
    Entity(parent=root, model="cube", color=_darker(c, 0.7), position=(0, 0.98 * s, 0), scale=(0.18 * s, 0.52 * s, 0.1 * s), rotation=(0, 0, 90))
    return (1.1 * s, 1.2 * s, 0.9 * s)


def _b_robot(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.75 * s, 0), scale=(0.72 * s, 0.9 * s, 0.38 * s))
    Entity(parent=root, model="cube", color=_darker(c, 1.2), position=(0, 1.35 * s, 0), scale=(0.56 * s, 0.42 * s, 0.42 * s))
    for x in (-0.18, 0.18):
        Entity(parent=root, model="sphere", color=color.cyan, position=(x * s, 1.4 * s, -0.22 * s), scale=0.08 * s, unlit=True)
    for x in (-0.5, 0.5):
        Entity(parent=root, model="cube", color=_darker(c, 0.8), position=(x * s, 0.75 * s, 0), scale=(0.16 * s, 0.64 * s, 0.16 * s))
    return (0.95 * s, 1.6 * s, 0.55 * s)


def _b_banana(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.45 * s, 0),
           scale=(0.22 * s, 0.9 * s, 0.18 * s), rotation=(0, 0, -22))
    Entity(parent=root, model="sphere", color=c, position=(-0.18 * s, 0.78 * s, 0), scale=(0.22 * s, 0.18 * s, 0.18 * s))
    Entity(parent=root, model="sphere", color=c, position=(0.18 * s, 0.12 * s, 0), scale=(0.18 * s, 0.16 * s, 0.16 * s))
    Entity(parent=root, model="cube", color=_darker(c, 0.45), position=(-0.32 * s, 0.9 * s, 0), scale=(0.08 * s, 0.16 * s, 0.08 * s))
    return (0.75 * s, 1.1 * s, 0.3 * s)


def _b_chair(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.55 * s, 0), scale=(0.9 * s, 0.16 * s, 0.8 * s))
    Entity(parent=root, model="cube", color=c, position=(0, 1.12 * s, 0.34 * s), scale=(0.9 * s, 1.0 * s, 0.14 * s))
    for x in (-0.32, 0.32):
        for z in (-0.26, 0.26):
            Entity(parent=root, model="cube", color=_darker(c, 0.7), position=(x * s, 0.25 * s, z * s), scale=(0.12 * s, 0.5 * s, 0.12 * s))
    return (1.0 * s, 1.65 * s, 0.95 * s)


def _b_shoe(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0.05 * s, 0.24 * s, 0), scale=(1.05 * s, 0.34 * s, 0.46 * s))
    Entity(parent=root, model="sphere", color=c, position=(0.55 * s, 0.28 * s, 0), scale=(0.38 * s, 0.30 * s, 0.46 * s))
    Entity(parent=root, model="cube", color=color.rgb(0.95, 0.95, 0.9), position=(-0.22 * s, 0.44 * s, 0), scale=(0.38 * s, 0.06 * s, 0.42 * s))
    Entity(parent=root, model="cube", color=_darker(c, 0.35), position=(0.08 * s, 0.06 * s, 0), scale=(1.15 * s, 0.10 * s, 0.52 * s))
    return (1.25 * s, 0.62 * s, 0.58 * s)


def _b_car(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.38 * s, 0), scale=(1.25 * s, 0.45 * s, 0.65 * s))
    Entity(parent=root, model="cube", color=_darker(c, 1.15), position=(-0.05 * s, 0.72 * s, 0), scale=(0.68 * s, 0.38 * s, 0.55 * s))
    for x in (-0.42, 0.42):
        for z in (-0.34, 0.34):
            Entity(parent=root, model="sphere", color=color.rgb(0.05, 0.05, 0.06), position=(x * s, 0.13 * s, z * s), scale=0.22 * s)
    return (1.35 * s, 0.95 * s, 0.9 * s)


def _b_bed(root, c, s):
    Entity(parent=root, model="cube", color=c, position=(0, 0.42 * s, 0), scale=(1.75 * s, 0.32 * s, 1.05 * s))
    Entity(parent=root, model="cube", color=color.rgb(0.95, 0.93, 0.86), position=(0.18 * s, 0.64 * s, 0), scale=(1.25 * s, 0.16 * s, 0.95 * s))
    Entity(parent=root, model="cube", color=_darker(c, 0.7), position=(-0.78 * s, 0.92 * s, 0), scale=(0.18 * s, 0.9 * s, 1.08 * s))
    Entity(parent=root, model="cube", color=color.rgb(0.85, 0.88, 0.96), position=(-0.42 * s, 0.82 * s, 0), scale=(0.42 * s, 0.16 * s, 0.76 * s))
    return (1.9 * s, 1.35 * s, 1.2 * s)


BUILDERS = {
    "key": _b_key, "tool": _b_tool, "battery": _b_battery, "dog": _b_dog,
    "house": _b_house, "shadow": _b_shadow, "sphere": _b_sphere,
    "apple": _b_apple, "cup": _b_cup, "ball": _b_ball, "book": _b_book,
    "box": _b_box, "table": _b_table, "basket": _b_basket, "robot": _b_robot,
    "banana": _b_banana, "chair": _b_chair, "shoe": _b_shoe, "car": _b_car,
    "bed": _b_bed,
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
        self.collider_entity = collider_entity or anchor
        anchor.drone_anchor = height
        self.collider_entity.interactable = self

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
