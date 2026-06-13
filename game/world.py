"""
Voxel entity + procedural world generation.

The world is a flat grass field with a few hills, trees, a small pond, and
glowing "Word Ore" blocks scattered on top. Mining a Word Ore block triggers
an ESL challenge (wired up in main.py).
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

from ursina import Button, Entity, Vec3, color, scene

from . import blocks


class Voxel(Button):
    def __init__(self, position=(0, 0, 0), block_type: "blocks.BlockType" = blocks.GRASS):
        super().__init__(
            parent=scene,
            position=Vec3(*position),
            model="cube",
            origin_y=0.5,
            texture="white_cube",
            color=block_type.color,
            highlight_color=blocks.brighten(block_type.color, 0.25),
            collider="box",
            scale=1,
        )
        self.block_type = block_type
        if block_type.unlit:
            self.unlit = True


class World:
    """Holds the voxel grid and builds the starting scene."""

    def __init__(self, radius: int, word_ore_count: int):
        self.radius = radius
        self.word_ore_count = word_ore_count
        self.voxels: Dict[Tuple[int, int, int], Voxel] = {}
        self.bedrock: Entity = None  # type: ignore

    # -- construction ------------------------------------------------------
    def key(self, pos) -> Tuple[int, int, int]:
        return (int(round(pos[0])), int(round(pos[1])), int(round(pos[2])))

    def add(self, position, block_type) -> Voxel:
        k = self.key(position)
        if k in self.voxels:
            return self.voxels[k]
        v = Voxel(position=k, block_type=block_type)
        self.voxels[k] = v
        return v

    def remove(self, voxel: Voxel):
        from ursina import destroy

        k = self.key(voxel.position)
        self.voxels.pop(k, None)
        destroy(voxel)

    def top_y(self, x: int, z: int) -> int:
        ys = [k[1] for k in self.voxels if k[0] == x and k[2] == z]
        return max(ys) if ys else -999

    def generate(self):
        r = self.radius

        # Invisible-ish bedrock floor so digging never drops you into the void.
        self.bedrock = Entity(
            model="cube",
            color=color.rgb(0.10, 0.10, 0.12),
            scale=(2 * r + 3, 1, 2 * r + 3),
            position=(0, -2.5, 0),
            collider="box",
        )

        # Grass field.
        for x in range(-r, r + 1):
            for z in range(-r, r + 1):
                self.add((x, 0, z), blocks.GRASS)

        self._carve_pond()
        self._raise_hills()
        self._plant_trees()
        self._scatter_word_ore()

    def _carve_pond(self):
        cx, cz = int(self.radius * 0.5), -int(self.radius * 0.4)
        for x in range(cx - 2, cx + 3):
            for z in range(cz - 2, cz + 3):
                k = (x, 0, z)
                if k not in self.voxels:
                    continue
                dist = ((x - cx) ** 2 + (z - cz) ** 2) ** 0.5
                if dist <= 1.6:
                    self._retype(k, blocks.WATER)
                elif dist <= 2.4:
                    self._retype(k, blocks.SAND)

    def _retype(self, k, block_type):
        from ursina import destroy

        old = self.voxels.get(k)
        if old:
            destroy(old)
        self.voxels[k] = Voxel(position=k, block_type=block_type)

    def _raise_hills(self):
        for _ in range(3):
            cx = random.randint(-self.radius + 2, self.radius - 2)
            cz = random.randint(-self.radius + 2, self.radius - 2)
            h = random.randint(1, 2)
            for y in range(1, h + 1):
                spread = h - y + 1
                for x in range(cx - spread, cx + spread + 1):
                    for z in range(cz - spread, cz + spread + 1):
                        if abs(x - cx) + abs(z - cz) <= spread:
                            bt = blocks.STONE if y < h else blocks.GRASS
                            self.add((x, y, z), bt)

    def _plant_trees(self):
        placed = 0
        attempts = 0
        while placed < 4 and attempts < 40:
            attempts += 1
            x = random.randint(-self.radius + 1, self.radius - 1)
            z = random.randint(-self.radius + 1, self.radius - 1)
            base = self.top_y(x, z)
            if base < 0 or self.voxels[(x, base, z)].block_type != blocks.GRASS:
                continue
            trunk = base + 3
            for y in range(base + 1, trunk + 1):
                self.add((x, y, z), blocks.WOOD)
            for lx in range(x - 1, x + 2):
                for lz in range(z - 1, z + 2):
                    self.add((lx, trunk, lz), blocks.LEAVES)
            self.add((x, trunk + 1, z), blocks.LEAVES)
            placed += 1

    def _scatter_word_ore(self):
        placed = 0
        attempts = 0
        while placed < self.word_ore_count and attempts < self.word_ore_count * 12:
            attempts += 1
            x = random.randint(-self.radius, self.radius)
            z = random.randint(-self.radius, self.radius)
            base = self.top_y(x, z)
            if base < 0:
                continue
            top_block = self.voxels[(x, base, z)].block_type
            if top_block in (blocks.WATER, blocks.WOOD, blocks.LEAVES):
                continue
            if (x, base + 1, z) in self.voxels:
                continue
            self.add((x, base + 1, z), blocks.WORD_ORE)
            placed += 1
