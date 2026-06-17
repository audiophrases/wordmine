"""
Peaceful progressive ESL rooms and levels for WordMine.

The original corridor/zone architecture has been repurposed into calm 3D
listening courses.  A level is a full course map.  A room is a section inside a
level.  Gates between rooms are manual interactables; the narrator says "Go to
the next room" and the learner discovers/uses the glowing doorway.
"""
from __future__ import annotations

from typing import List, Optional

from ursina import Entity, Vec3, color, destroy

from game.interactables import Interactable, build_decor, build_object

HALF_W = 6.0
BACK_Z = 19.0
FRONT_Z = -19.0
WALL_H = 3.4
DIV_A = 6.0
DIV_B = -6.0
DOOR_HALF = 1.25

_WALL_C = color.rgb(0.36, 0.40, 0.48)
_FLOOR_C = color.rgb(0.22, 0.26, 0.30)
_LEVEL_TINTS = {
    1: [color.rgb(0.25, 0.30, 0.36), color.rgb(0.26, 0.34, 0.30), color.rgb(0.32, 0.28, 0.36)],
    2: [color.rgb(0.34, 0.30, 0.24), color.rgb(0.24, 0.33, 0.35), color.rgb(0.30, 0.27, 0.37)],
}


class Level:
    def __init__(self, srs, *, level_number: int = 1, has_next_level: bool = False):
        self.srs = srs
        self.level_number = level_number
        self.has_next_level = has_next_level
        self.entities: List[Entity] = []
        self.interactables: List[Interactable] = []
        self.start_pos = Vec3(0, 1.2, 14)
        self.div_a, self.div_b = DIV_A, DIV_B
        self.exit_pos = Vec3(0, 0, -15.5)
        self.lesson_gate_1: Optional[Entity] = None
        self.lesson_gate_2: Optional[Entity] = None
        self.next_level_gate: Optional[Entity] = None
        self.trophy: Optional[Entity] = None

        self._build_shell()
        if level_number == 2:
            self._build_level_two_rooms()
        else:
            self._build_level_one_rooms()

    # -- helpers -----------------------------------------------------------
    def _track(self, e):
        self.entities.append(e)
        return e

    def _box(self, pos, scale, col, collider="box", **kw):
        return self._track(Entity(model="cube", position=pos, scale=scale,
                                  color=col, collider=collider,
                                  texture="white_cube", **kw))

    def _wall_seg(self, x1, x2, zc, thick=0.3):
        if x2 - x1 <= 0.01:
            return
        self._box(((x1 + x2) / 2, WALL_H / 2, zc), (x2 - x1, WALL_H, thick), _WALL_C)

    def _add_inter(self, inter):
        self.interactables.append(inter)
        if inter.root not in self.entities:
            self.entities.append(inter.root)
        return inter

    def _pedestal(self, x, z, tint=color.rgb(0.34, 0.36, 0.42)):
        self._box((x, 0.35, z), (0.9, 0.7, 0.9), tint)
        return 0.75

    def _slab(self, pos, scale, col):
        return self._track(Entity(model="cube", position=pos, scale=scale,
                                  color=col, collider="box", unlit=True))

    def _lesson_object(self, word_id, x, z, *, scale=None, kind="lesson", **kwargs):
        word = self.srs.word(word_id)
        if not word:
            return None
        top = self._pedestal(x, z)
        if scale is not None:
            kwargs["scale"] = scale
        return self._add_inter(build_object(word, (x, top, z), kind=kind, **kwargs))

    def _gate(self, barrier, anchor_pos, *, transition: Optional[str] = None):
        anchor = self._track(Entity(position=anchor_pos))
        payload = {"barrier": barrier}
        if transition:
            payload["transition"] = transition
        return self._add_inter(Interactable(
            anchor, "gate", word=self.srs.word("open"), collider_entity=barrier,
            height=1.8, payload=payload))

    # -- shell -------------------------------------------------------------
    def _build_shell(self):
        length = BACK_Z - FRONT_Z
        tints = _LEVEL_TINTS.get(self.level_number, _LEVEL_TINTS[1])
        self._box((0, -0.2, (BACK_Z + FRONT_Z) / 2), (2 * HALF_W, 0.4, length),
                  _FLOOR_C, texture_scale=(2 * HALF_W, length))
        # subtle room carpets / color zones
        self._box((0, -0.17, 12.2), (11.4, 0.04, 11.8), tints[0], collider=None)
        self._box((0, -0.16, 0.0), (11.4, 0.04, 11.7), tints[1], collider=None)
        self._box((0, -0.15, -12.3), (11.4, 0.04, 12.0), tints[2], collider=None)

        # outer walls
        self._box((0, WALL_H / 2, BACK_Z), (2 * HALF_W, WALL_H, 0.3), _WALL_C)
        if self.has_next_level:
            self._wall_seg(-HALF_W, -DOOR_HALF, FRONT_Z)
            self._wall_seg(DOOR_HALF, HALF_W, FRONT_Z)
        else:
            self._box((0, WALL_H / 2, FRONT_Z), (2 * HALF_W, WALL_H, 0.3), _WALL_C)
        self._box((-HALF_W, WALL_H / 2, 0), (0.3, WALL_H, length), _WALL_C)
        self._box((HALF_W, WALL_H / 2, 0), (0.3, WALL_H, length), _WALL_C)

        # inner dividers with central lesson gates
        for zc in (DIV_A, DIV_B):
            self._wall_seg(-HALF_W, -DOOR_HALF, zc)
            self._wall_seg(DOOR_HALF, HALF_W, zc)

        self.lesson_gate_1 = self._slab((0, WALL_H / 2, DIV_A),
                                        (2 * DOOR_HALF, WALL_H, 0.25),
                                        color.rgba(0.25, 0.75, 1.0, 0.48))
        self.lesson_gate_2 = self._slab((0, WALL_H / 2, DIV_B),
                                        (2 * DOOR_HALF, WALL_H, 0.25),
                                        color.rgba(0.55, 0.95, 0.45, 0.48))
        self._gate(self.lesson_gate_1, (0, 1.5, DIV_A + 0.25))
        self._gate(self.lesson_gate_2, (0, 1.5, DIV_B + 0.25))

        if self.has_next_level:
            self.next_level_gate = self._slab((0, WALL_H / 2, FRONT_Z),
                                              (2 * DOOR_HALF, WALL_H, 0.25),
                                              color.rgba(0.98, 0.72, 1.0, 0.50))
            self._gate(self.next_level_gate, (0, 1.5, FRONT_Z + 0.35), transition="level")

    # -- level 1 -----------------------------------------------------------
    def _build_level_one_rooms(self):
        # room 1: very easy single-word listening
        self._lesson_object("apple", -3.6, 13.0, scale=1.1)
        self._lesson_object("cup", 3.4, 12.2, scale=1.0)
        self._lesson_object("ball", -2.1, 8.8, scale=1.0)
        self._lesson_object("book", 2.0, 8.4, scale=1.15)
        self._track(build_decor("robot", (0, 0, 16.2), [0.55, 0.68, 0.88], scale=1.0))

        # room 2: find/touch concrete classroom objects
        self._lesson_object("key", -4.0, 2.7, scale=1.2)
        self._lesson_object("box", 3.6, 2.3, scale=1.0)
        self._lesson_object("table", -3.0, -2.6, scale=1.0)
        self._lesson_object("basket", 3.1, -2.8, scale=1.0)
        self._track(build_decor("dog", (0.0, 0, 0.0), [0.56, 0.38, 0.22], scale=1.2))

        # room 3: gentle mixed review with duplicate items
        self._lesson_object("robot", 0, -10.0, scale=1.15)
        self._lesson_object("apple", -3.8, -13.0, scale=1.0)
        self._lesson_object("cup", 3.8, -13.2, scale=1.0)
        self._lesson_object("book", -2.0, -16.0, scale=1.0)
        self._lesson_object("ball", 2.0, -16.0, scale=1.0)
        if not self.has_next_level:
            self._build_trophy()

    # -- level 2 -----------------------------------------------------------
    def _build_level_two_rooms(self):
        # room 1: new concrete words
        self._lesson_object("banana", -3.6, 13.0, scale=1.05)
        self._lesson_object("chair", 3.4, 12.2, scale=1.0)
        self._lesson_object("shoe", -2.1, 8.8, scale=1.0)
        self._lesson_object("car", 2.0, 8.4, scale=1.05)
        self._track(build_decor("robot", (0, 0, 16.2), [0.70, 0.62, 0.92], scale=1.0))

        # room 2: simple find/touch review with one familiar object pair
        self._lesson_object("bed", -4.0, 2.7, scale=0.95)
        self._lesson_object("dog", 3.6, 2.3, scale=1.0)
        self._lesson_object("table", -3.0, -2.6, scale=1.0)
        self._lesson_object("basket", 3.1, -2.8, scale=1.0)

        # room 3: color/size adjectives, simple placement, and level-two review
        self._lesson_object("robot", 0, -8.4, scale=1.0)
        self._lesson_object("red_apple", -4.5, -10.6, repeatable=True, cooldown=0.2)
        self._lesson_object("green_apple", -2.4, -10.6, repeatable=True, cooldown=0.2)
        self._lesson_object("big_apple", -4.4, -13.0, repeatable=True, cooldown=0.2)
        self._lesson_object("small_apple", -2.3, -13.0, repeatable=True, cooldown=0.2)
        self._lesson_object("basket", 2.6, -10.2, scale=0.95)
        self._lesson_object("table", 4.4, -10.2, scale=0.9)
        self._lesson_object("box", 2.6, -13.4, scale=0.9)
        self._lesson_object("chair", 4.4, -13.4, scale=0.75)
        self._lesson_object("banana", -4.2, -16.4, scale=0.9)
        self._lesson_object("shoe", -1.2, -16.4, scale=0.9)
        self._lesson_object("car", 1.8, -16.4, scale=0.9)
        self._build_trophy()

    def _build_trophy(self):
        self._box((0, 0.2, self.exit_pos.z), (1.4, 0.4, 1.4), color.rgb(0.45, 0.48, 0.54))
        self.trophy = self._track(Entity(model="sphere", color=color.gold, unlit=True,
                                         position=(0, 1.35, self.exit_pos.z), scale=0.7))

    # -- runtime -----------------------------------------------------------
    def update(self, dt):
        for inter in self.interactables:
            inter.tick(dt)

    def destroy(self):
        for e in self.entities:
            destroy(e)
        self.entities.clear()
        self.interactables.clear()
