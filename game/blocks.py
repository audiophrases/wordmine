"""Block type registry for the voxel world."""
from __future__ import annotations

from dataclasses import dataclass

from ursina import color


def brighten(c, amount=0.25):
    """Return a lighter copy of an Ursina Color (for hover highlight)."""
    return color.rgba(
        min(1.0, c[0] + amount),
        min(1.0, c[1] + amount),
        min(1.0, c[2] + amount),
        1.0,
    )


@dataclass(frozen=True)
class BlockType:
    id: str
    name: str
    color: object          # ursina Color
    placeable: bool = True  # shows up in the hotbar / can be placed
    is_word_ore: bool = False
    unlit: bool = False     # glow regardless of lighting (word ore)


GRASS = BlockType("grass", "Grass", color.hsv(110, 0.55, 0.62))
DIRT = BlockType("dirt", "Dirt", color.rgb(0.45, 0.30, 0.18))
STONE = BlockType("stone", "Stone", color.rgb(0.52, 0.52, 0.55))
SAND = BlockType("sand", "Sand", color.rgb(0.85, 0.78, 0.50))
WOOD = BlockType("wood", "Wood", color.rgb(0.50, 0.34, 0.18))
LEAVES = BlockType("leaves", "Leaves", color.hsv(122, 0.55, 0.45))
WATER = BlockType("water", "Water", color.rgb(0.25, 0.50, 0.85), placeable=False)
WORD_ORE = BlockType(
    "word_ore", "Word Ore", color.hsv(46, 0.95, 1.0),
    placeable=False, is_word_ore=True, unlit=True,
)

# Order shown in the hotbar (keys 1..6).
HOTBAR = [GRASS, DIRT, STONE, SAND, WOOD, LEAVES]

ALL = [GRASS, DIRT, STONE, SAND, WOOD, LEAVES, WATER, WORD_ORE]
BY_ID = {b.id: b for b in ALL}
