from __future__ import annotations

import struct

from ..data import addresses

DME_MISSING = ("dolphin-memory-engine is missing: Archipelago 0.6.7 or newer "
               "includes it; from a source checkout run ModuleUpdate or "
               "pip install dolphin-memory-engine")


class DolphinAdapter:
    def __init__(self) -> None:
        try:
            # noinspection PyPackageRequirements
            import dolphin_memory_engine
        except ImportError as exc:
            raise ImportError(DME_MISSING) from exc
        self._dme = dolphin_memory_engine

    def connect(self) -> bool:
        if not self._dme.is_hooked():
            self._dme.hook()
        return self._dme.is_hooked()

    def is_connected(self) -> bool:
        return self._dme.is_hooked()

    def disconnect(self) -> None:
        if self._dme.is_hooked():
            self._dme.un_hook()

    def read_u16(self, addr: int) -> int | None:
        raw = self.read(addr, addresses.U16_SIZE)
        return struct.unpack(">H", raw)[0] if raw else None

    def read(self, addr: int, size: int) -> bytes | None:
        try:
            return self._dme.read_bytes(addr, size)
        except RuntimeError:
            return None

    def read_u32(self, addr: int) -> int | None:
        raw = self.read(addr, addresses.U32_SIZE)
        return struct.unpack(">I", raw)[0] if raw else None

    def write_u16(self, addr: int, value: int) -> bool:
        return self.write(addr, struct.pack(">H", value))

    def write(self, addr: int, data: bytes) -> bool:
        try:
            self._dme.write_bytes(addr, data)
            return True
        except RuntimeError:
            return False

    def write_u32(self, addr: int, value: int) -> bool:
        return self.write(addr, struct.pack(">I", value))
