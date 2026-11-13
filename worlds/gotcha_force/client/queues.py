from __future__ import annotations

import struct
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from ..data.addresses import (
    QREC_CAP,
    QREC_CAP_MAX,
    QREC_DELAYS,
    QREC_FLAGS,
    QREC_ID,
    QREC_LOOP_BACK_OFF,
    QREC_LOOP_MARK_OFF,
    QREC_POS,
    QREC_TARGET,
    STAGE_ENTRY,
    STAGE_QUEUE2_OFF,
    U16_SIZE,
)
from ..data.packs import QUEUE2, QUEUE_ARENA_HI, QUEUE_ARENA_LO, QUEUE_RECORD, STAGE_OBJ_TABLE
from ..logic import enemies
from ..logic.enemies import Escort

LOOP_MARK: Final = 0x7FFF

IMMEDIATE: Final = 0

QUEUE_TERMINATOR_RECORDS: Final = 1

_INSERT: Final = "ins"
_REMOVE: Final = "del"


@dataclass
class QueueEdit:
    inserts: dict[int, tuple[Escort, ...]] = field(default_factory=dict)
    removes: set[int] = field(default_factory=set)

    @property
    def delta(self) -> int:
        return sum(len(v) for v in self.inserts.values()) - len(self.removes)


def queue_with_inserts(
    queue: bytes, ptr: int, inserts: Mapping[int, Sequence[Escort]], removes: Iterable[int] = ()
) -> bytes:
    record_count = len(queue) // QUEUE_RECORD
    recs = [queue[i * QUEUE_RECORD : (i + 1) * QUEUE_RECORD] for i in range(record_count)]

    def index_of(cell: int) -> int:
        idx, remainder = divmod(cell - QREC_ID - ptr, QUEUE_RECORD)
        if remainder or not (0 <= idx < record_count - QUEUE_TERMINATOR_RECORDS):
            raise ValueError(f"cell outside the queue: {cell:#x}")
        return idx

    def adjust_loops(idx: int, delta: int) -> None:
        for later in range(idx + 1, len(recs)):
            if struct.unpack_from(">h", recs[later], QREC_LOOP_MARK_OFF)[0] == LOOP_MARK:
                back = struct.unpack_from(">h", recs[later], QREC_LOOP_BACK_OFF)[0]
                if later - back <= idx:
                    record = bytearray(recs[later])
                    struct.pack_into(">h", record, QREC_LOOP_BACK_OFF, back + delta)
                    recs[later] = bytes(record)

    ops: list[tuple[int, str, Sequence[Escort]]] = []
    ops.extend((index_of(cell), _INSERT, tuple(escorts)) for cell, escorts in inserts.items())
    ops.extend((index_of(cell), _REMOVE, ()) for cell in removes)
    for idx, edit, escorts in sorted(ops, reverse=True):
        if edit == _INSERT:
            new_records = [escort_record(recs[idx], e) for e in escorts]
            adjust_loops(idx, len(new_records))
            recs[idx + 1 : idx + 1] = new_records
        else:
            if recs[idx][QREC_TARGET]:
                raise ValueError(f"a TARGET is not removed: index {idx}")
            adjust_loops(idx, -1)
            del recs[idx]
    return b"".join(recs)


def escort_record(leader: bytes, escort: Escort) -> bytes:
    record = bytearray(leader)
    struct.pack_into(">hh", record, QREC_DELAYS, IMMEDIATE, IMMEDIATE)
    cap = struct.unpack_from(">h", leader, QREC_CAP)[0]
    struct.pack_into(">h", record, QREC_CAP, min(max(cap, 0) + escort.cap, QREC_CAP_MAX))
    struct.pack_into(">H", record, QREC_ID, escort.borg)
    if escort.flags is not None:
        record[QREC_FLAGS] = escort.flags
    record[QREC_TARGET] = 0
    x, y, z = struct.unpack_from(">fff", leader, QREC_POS)
    dx, dy, dz = escort.dpos
    struct.pack_into(">fff", record, QREC_POS, x + dx, y + dy, z + dz)
    return bytes(record)


def cell_of(ptr: int, idx: int) -> int:
    return ptr + idx * QUEUE_RECORD + QREC_ID


def custom_queue_plan(inserts: Mapping[int, Sequence[Escort]], removes: Iterable[int] = ()) -> dict[int, QueueEdit]:
    out: dict[int, QueueEdit] = {}
    for cell, escorts in inserts.items():
        out.setdefault(enemies.cell_chapter(cell), QueueEdit()).inserts[cell] = tuple(escorts)
    for cell in removes:
        out.setdefault(enemies.cell_chapter(cell), QueueEdit()).removes.add(cell)
    return out


def arena_layout(plan: Mapping[int, QueueEdit]) -> dict[int, int]:
    out: dict[int, int] = {}
    cursor = QUEUE_ARENA_LO
    for chapter in sorted(plan):
        records = QUEUE2[chapter].records + plan[chapter].delta
        size = records * QUEUE_RECORD
        if cursor + size > QUEUE_ARENA_HI:
            raise ValueError("the queues do not fit in the arena")
        out[chapter] = cursor
        cursor += size
    return out


def apply_overrides(
    blob: bytes, base: int, u16_writes: Mapping[int, int | None], u8_writes: Mapping[int, int]
) -> bytes:
    out = bytearray(blob)
    end = base + len(out)
    for addr, value in u16_writes.items():
        if value is not None and base <= addr and addr + U16_SIZE <= end:
            struct.pack_into(">H", out, addr - base, value)
    for addr, value in u8_writes.items():
        if base <= addr < end:
            out[addr - base] = value
    return bytes(out)


def stage_table_entry(chapter: int) -> int:
    return STAGE_OBJ_TABLE + STAGE_ENTRY * chapter + STAGE_QUEUE2_OFF
