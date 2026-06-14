"""
The Chaser -- a Security Drone that relentlessly hunts the player.

It follows a *breadcrumb trail* of the player's recent positions, so it tracks
through doorways and around walls without clipping or fancy pathfinding. It is
a little slower than the player, so a moving player gains ground -- but echoing
words takes time, and the drone keeps accelerating. Action verbs interrupt it:
  freeze() -> "stop"   block() -> "close"   lose() -> "hide"
If it gets within the catch radius (and you aren't hidden), it's "Busted".
"""
from __future__ import annotations

import math
from collections import deque

from ursina import Entity, Vec3, color, time


def _dist_xz(a, b) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2)


class SecurityDrone:
    FLY_Y = 1.4

    def __init__(self, spawn_pos, base_speed, accel, max_speed,
                 catch_radius, grace_secs):
        self.base_speed = base_speed
        self.accel = accel
        self.max_speed = max_speed
        self.catch_radius = catch_radius
        self.grace_secs = grace_secs

        self.root = Entity(position=(spawn_pos[0], self.FLY_Y, spawn_pos[2]))
        self.body = Entity(parent=self.root, model="sphere", scale=0.55,
                           color=color.rgb(0.55, 0.08, 0.08), collider="box")
        self.eye = Entity(parent=self.root, model="sphere", scale=0.2,
                          position=(0, 0, 0.26), color=color.rgb(1, 0.2, 0.1), unlit=True)
        self.ring = Entity(parent=self.root, model="cube", scale=(0.95, 0.05, 0.05),
                           color=color.rgba(1, 0.3, 0.2, 0.8), unlit=True)
        self.ring2 = Entity(parent=self.root, model="cube", scale=(0.05, 0.05, 0.95),
                            color=color.rgba(1, 0.3, 0.2, 0.8), unlit=True)

        self.crumbs = deque(maxlen=500)
        self.reset(spawn_pos)

    # -- state ------------------------------------------------------------
    def reset(self, spawn_pos):
        self.root.position = (spawn_pos[0], self.FLY_Y, spawn_pos[2])
        self.crumbs.clear()
        self.frozen = 0.0
        self.blocked = 0.0
        self.lost = 0.0
        self.chase_time = 0.0
        self.speed = self.base_speed
        self.active = False

    def freeze(self, secs):
        self.frozen = max(self.frozen, secs)

    def block(self, secs):
        self.blocked = max(self.blocked, secs)

    def lose(self, secs):
        self.lost = max(self.lost, secs)

    @property
    def stunned(self) -> bool:
        return self.frozen > 0 or self.blocked > 0

    def add_crumb(self, pos):
        if not self.crumbs or _dist_xz(self.crumbs[-1], pos) > 0.9:
            self.crumbs.append(Vec3(pos[0], self.FLY_Y, pos[2]))

    def distance_to(self, player) -> float:
        return _dist_xz(self.root.world_position, player.world_position)

    def danger(self, player, falloff=14.0) -> float:
        """0 (far / safe) .. 1 (about to be caught)."""
        if not self.active:
            return 0.0
        d = self.distance_to(player)
        return max(0.0, min(1.0, 1.0 - d / falloff))

    # -- per-frame --------------------------------------------------------
    def update(self, player, hidden: bool) -> bool:
        dt = time.dt
        self._animate(dt)

        self.frozen = max(0.0, self.frozen - dt)
        self.blocked = max(0.0, self.blocked - dt)
        self.lost = max(0.0, self.lost - dt)
        self.chase_time += dt
        self.speed = min(self.max_speed, self.base_speed + self.accel * self.chase_time)

        if not self.active:
            if self.chase_time >= self.grace_secs:
                self.active = True
            return False
        if self.stunned:
            return False

        tracking = not hidden and self.lost <= 0
        target = None
        if tracking:
            while self.crumbs and _dist_xz(self.root.world_position, self.crumbs[0]) < 0.6:
                self.crumbs.popleft()
            target = self.crumbs[0] if self.crumbs else player.world_position
        elif self.crumbs:
            target = self.crumbs[0]  # drift toward last known location, slowly

        if target is not None:
            speed = self.speed if tracking else self.speed * 0.35
            self._move_toward(target, speed, dt)

        if tracking and _dist_xz(self.root.world_position, player.world_position) < self.catch_radius:
            return True  # BUSTED
        return False

    def _move_toward(self, target, speed, dt):
        pos = self.root.world_position
        dx, dz = target[0] - pos[0], target[2] - pos[2]
        dlen = math.hypot(dx, dz)
        if dlen > 1e-4:
            step = min(speed * dt, dlen)
            self.root.x += dx / dlen * step
            self.root.z += dz / dlen * step
            self.root.look_at(Vec3(target[0], self.FLY_Y, target[2]))
        self.root.y = self.FLY_Y

    def _animate(self, dt):
        self.ring.rotation_y += dt * 520
        self.ring2.rotation_y += dt * 520
        self.root.y = self.FLY_Y + math.sin(time.time() * 4) * 0.08
        glow = 0.6 + 0.4 * math.sin(time.time() * (10 if self.active else 3))
        self.eye.color = color.rgba(1, 0.2 * glow, 0.1 * glow, 1)
