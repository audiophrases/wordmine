"""
The heist facility: a structured 3-zone level (built fresh each attempt so a
"Busted" reset is trivial -- just destroy and rebuild).

  Zone 1 (Scavenge, +Z): grab key, tool & battery to power the first gate.
  Zone 2 (The Chase, mid): a corridor of action-verb obstacles
         -- open a door, stop a moving trap, hit a run pad, close a door behind.
  Zone 3 (The Lockout, -Z): the SRS gate demands your weakest word; then the
         trophy / exit.

Everything is 1 unit = 1 metre so props read at a natural, human scale.
"""
from __future__ import annotations

import math
import random
from typing import List

from ursina import Entity, Vec3, color, destroy, time

import config
from game.interactables import Interactable, build_decor, build_object

HALF_W = 6.0
BACK_Z = 19.0     # Zone-1 end (player start)
FRONT_Z = -19.0   # Zone-3 end (exit)
WALL_H = 3.4
DIV_A = 6.0       # Zone 1 | 2 divider
DIV_B = -6.0      # Zone 2 | 3 divider
DOOR_HALF = 1.2   # half-width of each doorway

_WALL_C = color.rgb(0.34, 0.36, 0.42)
_FLOOR_C = color.rgb(0.20, 0.21, 0.25)


class TrapGate:
    """A security gate that slides across the corridor; "stop" freezes it."""

    def __init__(self, center, span=3.0, speed=2.2):
        self.center = Vec3(*center)
        self.span = span
        self.speed = speed
        self.t = random.uniform(0, 6.28)
        self.frozen = 0.0
        self.entity = Entity(model="cube", color=color.rgb(0.9, 0.45, 0.1),
                             scale=(1.0, 3.0, 0.35), position=self.center,
                             collider="box")
        Entity(parent=self.entity, model="cube", color=color.rgba(1, 0.8, 0.2, 1),
               scale=(1.05, 0.12, 0.4), position=(0, 0.3, 0), unlit=True)

    def freeze(self, secs):
        self.frozen = max(self.frozen, secs)

    def update(self, dt):
        if self.frozen > 0:
            self.frozen -= dt
            self.entity.color = color.rgb(0.25, 0.6, 1.0)  # frozen = blue
            return
        self.entity.color = color.rgb(0.9, 0.45, 0.1)
        self.t += dt * self.speed
        self.entity.x = self.center.x + math.sin(self.t) * self.span


class Level:
    def __init__(self, srs):
        self.srs = srs
        self.entities: List[Entity] = []
        self.interactables: List[Interactable] = []
        self.traps: List[TrapGate] = []

        self.start_pos = Vec3(0, 1.2, 13)
        self.chaser_spawn = (0, 0, 13 + config.CHASER_SPAWN_BEHIND)
        self.div_a, self.div_b = DIV_A, DIV_B

        self.power_barrier = None
        self.power_door = None
        self.final_gate = None
        self.trophy_pos = Vec3(0, 0, -15)

        self._build_shell()
        self._build_zone1()
        self._build_zone2()
        self._build_zone3()

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

    def _verb_station(self, kind, anchor_pos, collider_entity, payload=None,
                      height=1.6, repeatable=False, cooldown=0.0):
        anchor = self._track(Entity(position=anchor_pos))
        return self._add_inter(Interactable(
            anchor, kind, word=self.srs.word(kind), collider_entity=collider_entity,
            height=height, payload=payload or {}, repeatable=repeatable,
            cooldown=cooldown))

    def _slab(self, pos, scale, col):
        """A glowing door/gate barrier (collider blocks; unlit so it reads as energy)."""
        return self._track(Entity(model="cube", position=pos, scale=scale,
                                  color=col, collider="box", unlit=True))

    # -- shell -------------------------------------------------------------
    def _build_shell(self):
        length = BACK_Z - FRONT_Z
        self._box((0, -0.2, (BACK_Z + FRONT_Z) / 2), (2 * HALF_W, 0.4, length),
                  _FLOOR_C, texture_scale=(2 * HALF_W, length))
        # outer walls
        self._box((0, WALL_H / 2, BACK_Z), (2 * HALF_W, WALL_H, 0.3), _WALL_C)
        self._box((0, WALL_H / 2, FRONT_Z), (2 * HALF_W, WALL_H, 0.3), _WALL_C)
        self._box((-HALF_W, WALL_H / 2, 0), (0.3, WALL_H, length), _WALL_C)
        self._box((HALF_W, WALL_H / 2, 0), (0.3, WALL_H, length), _WALL_C)
        # inner dividers with central doorways
        for zc in (DIV_A, DIV_B):
            self._wall_seg(-HALF_W, -DOOR_HALF, zc)
            self._wall_seg(DOOR_HALF, HALF_W, zc)

    # -- zone 1: scavenge --------------------------------------------------
    def _pedestal(self, x, z):
        self._box((x, 0.45, z), (0.7, 0.9, 0.7), color.rgb(0.3, 0.32, 0.38))
        return 0.9

    def _build_zone1(self):
        spots = [(-3.5, 11), (3.5, 9.5), (0, 7.6)]
        for wid, (x, z) in zip(config.SCAVENGE_TARGETS, spots):
            word = self.srs.word(wid)
            if not word:
                continue
            top = self._pedestal(x, z)
            self._add_inter(build_object(word, (x, top, z), kind="scavenge"))
        # a dog, purely scenery -- a scale check that you can "see a dog"
        self._track(build_decor("dog", (-4.6, 0, 12.5), [0.5, 0.36, 0.2], scale=1.0))

        # Zone1 -> Zone2 power door (locked until scavenging is done)
        self.power_barrier = self._slab((0, WALL_H / 2, DIV_A),
                                        (2 * DOOR_HALF, WALL_H, 0.25),
                                        color.rgba(1.0, 0.5, 0.15, 0.55))
        self.power_door = self._verb_station(
            "open", (0, 1.4, DIV_A + 0.2), self.power_barrier,
            payload={"barrier": self.power_barrier, "requires_power": True})

    # -- zone 2: the chase -------------------------------------------------
    def _add_door_inter(self, word_id, collider_entity, anchor_pos, payload, **kw):
        anchor = self._track(Entity(position=anchor_pos))
        return self._add_inter(Interactable(
            anchor, word_id if word_id in ("open", "close", "stop", "hide", "run") else word_id,
            word=self.srs.word(word_id), collider_entity=collider_entity,
            height=1.6, payload=payload, **kw))

    def _build_zone2(self):
        # CLOSE: a wall console (just past the power door) that slams it behind you
        console = self._box((-5.3, 1.0, 4.6), (0.5, 1.2, 0.8),
                            color.rgb(0.3, 0.35, 0.45))
        self._verb_station("close", (-4.7, 1.4, 4.6), console, height=1.2,
                           repeatable=True, cooldown=config.CLOSE_BLOCK_SECS + 4,
                           payload={"door_barrier": self.power_barrier})

        # RUN: a glowing floor pad
        pad = self._track(Entity(model="cube", color=color.rgba(0.2, 1.0, 0.6, 0.85),
                                 position=(2.6, 0.06, 3.0), scale=(1.7, 0.12, 1.7),
                                 unlit=True, collider="box"))
        self._verb_station("run", (2.6, 0.5, 3.0), pad, height=0.5,
                           repeatable=True, cooldown=6.0)

        # OPEN: a barrier across the corridor
        open_bar = self._slab((0, 1.5, 1.0), (2 * HALF_W - 0.6, 3.0, 0.25),
                              color.rgba(0.2, 0.7, 1.0, 0.5))
        self._verb_station("open", (0, 1.6, 1.2), open_bar, payload={"barrier": open_bar})

        # HIDE: a small house to duck behind
        self._add_inter(build_object(self.srs.word("hide"), (4.3, 0, -1.0),
                                     kind="hide", shape="house",
                                     color=[0.5, 0.5, 0.58], scale=1.0,
                                     repeatable=True, cooldown=config.HIDE_SECS + 3))

        # STOP: a sliding trap gate
        trap = TrapGate((0, 1.5, -3.5), span=3.2, speed=2.0)
        self.entities.append(trap.entity)
        self.traps.append(trap)
        self._add_inter(Interactable(trap.entity, "stop", word=self.srs.word("stop"),
                                     collider_entity=trap.entity, height=2.0,
                                     payload={"trap": trap}))

    # -- zone 3: the lockout -----------------------------------------------
    def _build_zone3(self):
        pool = [self.srs.word(w) for w in
                ("key", "tool", "battery", "open", "close", "stop", "hide", "run")
                if self.srs.word(w)]
        gate_bar = self._slab((0, WALL_H / 2, DIV_B), (2 * DOOR_HALF, WALL_H, 0.25),
                              color.rgba(1.0, 0.2, 0.3, 0.6))
        anchor = self._track(Entity(position=(0, 1.6, DIV_B + 0.2)))
        self.final_gate = self._add_inter(Interactable(
            anchor, "gate", word_provider=lambda: self.srs.demand_word(pool=pool),
            collider_entity=gate_bar, height=1.8,
            payload={"barrier": gate_bar}))

        # the trophy / exit
        self._box((0, 0.25, self.trophy_pos.z), (1.4, 0.5, 1.4), color.rgb(0.4, 0.4, 0.45))
        self.trophy = self._track(Entity(model="sphere", color=color.gold, unlit=True,
                                         position=(0, 1.5, self.trophy_pos.z), scale=0.8))

    # -- runtime -----------------------------------------------------------
    def update(self, dt):
        for inter in self.interactables:
            inter.tick(dt)
        for trap in self.traps:
            trap.update(dt)
        if self.trophy:
            self.trophy.rotation_y += dt * 60

    def destroy(self):
        for e in self.entities:
            destroy(e)
        self.entities.clear()
        self.interactables.clear()
        self.traps.clear()
