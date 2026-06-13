"""A minimal hotbar-style inventory: counts per block id + a selected slot."""
from __future__ import annotations

from typing import List

from . import blocks


class Inventory:
    def __init__(self, slot_blocks: List["blocks.BlockType"] = None, starting: int = 16):
        slot_blocks = slot_blocks or blocks.HOTBAR
        self.order = [b.id for b in slot_blocks]
        self.counts = {b.id: starting for b in slot_blocks}
        self.selected_index = 0

    @property
    def selected_id(self) -> str:
        return self.order[self.selected_index]

    @property
    def selected_block(self) -> "blocks.BlockType":
        return blocks.BY_ID[self.selected_id]

    def select(self, index: int):
        if 0 <= index < len(self.order):
            self.selected_index = index

    def scroll(self, direction: int):
        self.selected_index = (self.selected_index + direction) % len(self.order)

    def count(self, block_id: str) -> int:
        return self.counts.get(block_id, 0)

    def add(self, block_id: str, n: int = 1):
        if block_id not in self.counts:
            # picked up something not originally in the hotbar -> append a slot
            self.order.append(block_id)
            self.counts[block_id] = 0
        self.counts[block_id] += n

    def take(self, block_id: str, n: int = 1) -> bool:
        if self.counts.get(block_id, 0) >= n:
            self.counts[block_id] -= n
            return True
        return False
