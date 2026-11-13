from __future__ import annotations

from typing import TYPE_CHECKING

from ..data import addresses

if TYPE_CHECKING:
    from . import GotchaForceContext
    from .dolphin import DolphinAdapter


def in_mem1(pointer: int | None) -> bool:
    return pointer is not None and addresses.MEM1_LO <= pointer < addresses.MEM1_HI


class Stage:
    dolphin: DolphinAdapter
    ctx: GotchaForceContext

    def _savedata(self) -> int | None:
        pointer = self.dolphin.read_u32(addresses.SAVEDATA_PTR)
        if pointer is None or not in_mem1(pointer):
            return None
        borg_count = self.dolphin.read_u16(pointer + addresses.SAVE_N_BORGS)
        if borg_count is None or not (1 <= borg_count <= addresses.COLLECTION_SLOTS):
            return None
        return pointer

    def _box2(self) -> int | None:
        pointer = self.dolphin.read_u32(addresses.BOX2_PTR)
        return pointer if in_mem1(pointer) else None

    def _write_if_diff(self, addr: int, desired: bytes) -> None:
        current = self.dolphin.read(addr, len(desired))
        if current is not None and current != desired:
            self.dolphin.write(addr, desired)
