from __future__ import annotations

import os
import shutil
import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, NamedTuple

from .data import dol_patch

ALIGN: Final = 0x20
AP_SUFFIX: Final = " [AP]"
WORD_SIZE: Final = 4

BOOT_LEN: Final = 0x440
BOOT_DOL_OFFSET: Final = 0x420
BOOT_FST_OFFSET: Final = 0x424
BOOT_RECORD: Final = struct.Struct(">4I")

DOL_SECTIONS: Final = 18
DOL_OFFSETS: Final = 0x00
DOL_ADDRESSES: Final = 0x48
DOL_SIZES: Final = 0x90
DOL_HEADER_LEN: Final = 0xE4
SECTION_TABLE: Final = struct.Struct(f">{DOL_SECTIONS}I")

FST_ENTRY_LEN: Final = 12
FST_ENTRY_TYPE_OFF: Final = 0
FST_FILE_ENTRY: Final = 0
FST_FILE_OFFSET_OFF: Final = 4
FST_ROOT_ENTRY_COUNT_OFF: Final = 8

DOL_VANILLA: Final = "vanilla"
DOL_CURRENT: Final = "current"
DOL_OLD: Final = "old"
DOL_UNEXPECTED: Final = "unexpected"

PATCH_CURRENT: Final = "current"
PATCH_OLD: Final = "old"
PATCH_NONE: Final = "none"

_MSG_DAMAGED = "The ISO file appears truncated or damaged."
_MSG_UNEXPECTED = ("The game data inside this ISO is not what the "
                   "patcher expects (maybe another mod or patch was "
                   "applied first). Please start from a clean, "
                   "unmodified USA ISO.")


class IsoPatchError(Exception):
    pass


class AlreadyPatchedError(IsoPatchError):
    pass


class OutdatedPatchError(IsoPatchError):
    pass


class DolHeader(NamedTuple):
    offsets: tuple[int, ...]
    addresses: tuple[int, ...]
    sizes: tuple[int, ...]


class Disc(NamedTuple):
    dol_offset: int
    fst_offset: int
    fst_size: int
    dol: bytes
    fst: bytes


ALL_HOOK_WORDS: tuple[tuple[int, int, int], ...] = (
    (dol_patch.MARKER_HOOK_ADDR, dol_patch.MARKER_HOOK_VANILLA, dol_patch.MARKER_HOOK_PATCHED),
    *dol_patch.OTHER_HOOK_WORDS,
)


@dataclass(frozen=True)
class PatchStatus:
    status: str | None
    words: dict[int, bool | None]


def patch_iso(src: str, dst: str | None = None) -> str:
    disc = _read_disc(src)
    new_dol = _build_dol(disc.dol)
    new_fst_offset = _align(disc.dol_offset + len(new_dol))
    if new_fst_offset + disc.fst_size > _first_file_offset(disc.fst):
        raise IsoPatchError(
            "Unexpected disc layout: there is no room for the patch. "
            "Please use a clean, unmodified USA ISO."
        )
    if dst is None:
        dst = default_output(src)
    if (os.path.normcase(os.path.abspath(dst))
            == os.path.normcase(os.path.abspath(src))):
        raise IsoPatchError(
            "The output file would overwrite the ISO you selected. "
            "Please choose a different output name."
        )
    _write_patched_copy(src, dst, disc, new_dol, new_fst_offset)
    if not verify_iso(dst):
        raise IsoPatchError(
            "Something went wrong: the patched copy did not pass the "
            f"final check. Please delete it and try again:\n{dst}"
        )
    return dst


def _read_disc(src: str) -> Disc:
    if not os.path.isfile(src):
        raise IsoPatchError(f"Could not find the file:\n{src}")
    try:
        with open(src, "rb") as f:
            boot = f.read(BOOT_LEN)
            if len(boot) < BOOT_LEN:
                raise IsoPatchError(
                    "This file is too small to be a GameCube ISO."
                )
            game_id = boot[:len(dol_patch.GAME_ID)]
            if game_id != dol_patch.GAME_ID:
                raise IsoPatchError(
                    f"This does not look like the USA version of Gotcha "
                    f"Force (game id {game_id.decode('ascii', 'replace')}, expected GG4E08). Please pick "
                    f"the USA ISO — the patch only works with that "
                    f"version."
                )
            dol_offset, fst_offset, fst_size, _ = BOOT_RECORD.unpack_from(boot, BOOT_DOL_OFFSET)
            f.seek(dol_offset)
            header = f.read(DOL_HEADER_LEN)
            if len(header) < DOL_HEADER_LEN:
                raise IsoPatchError(_MSG_DAMAGED)
            size = _dol_size(header)
            f.seek(dol_offset)
            dol = f.read(size)
            f.seek(fst_offset)
            fst = f.read(fst_size)
            if len(dol) != size or len(fst) != fst_size:
                raise IsoPatchError(_MSG_DAMAGED)
    except OSError as e:
        raise IsoPatchError(f"Could not read the ISO:\n{e}") from e
    return Disc(dol_offset, fst_offset, fst_size, dol, fst)


def _dol_size(header: bytes) -> int:
    sections = _dol_header(header)
    return max(offset + size for offset, size in zip(sections.offsets, sections.sizes, strict=True) if size)


def _dol_header(header: bytes) -> DolHeader:
    return DolHeader(SECTION_TABLE.unpack_from(header, DOL_OFFSETS),
                     SECTION_TABLE.unpack_from(header, DOL_ADDRESSES),
                     SECTION_TABLE.unpack_from(header, DOL_SIZES))


def _build_dol(dol: bytes) -> bytes:
    _reject_unless_vanilla(dol)
    new_dol = bytearray(dol)
    struct.pack_into(">I", new_dol, DOL_OFFSETS + WORD_SIZE * dol_patch.FREE_SECTION, len(dol))
    struct.pack_into(">I", new_dol, DOL_ADDRESSES + WORD_SIZE * dol_patch.FREE_SECTION, dol_patch.LOAD_ADDR)
    struct.pack_into(">I", new_dol, DOL_SIZES + WORD_SIZE * dol_patch.FREE_SECTION, len(dol_patch.ZONE))
    struct.pack_into(">I", new_dol, _marker_hook_file_offset(dol), dol_patch.MARKER_HOOK_PATCHED)
    for address, vanilla, word in dol_patch.OTHER_HOOK_WORDS:
        offset = _file_offset_of_ram_address(dol, address)
        if offset is None or _read_word(dol, offset) != vanilla:
            raise IsoPatchError(_MSG_UNEXPECTED)
        struct.pack_into(">I", new_dol, offset, word)
    new_dol += dol_patch.ZONE
    return bytes(new_dol)


def _reject_unless_vanilla(dol: bytes) -> None:
    state = _dol_patch_state(dol)
    if state == DOL_CURRENT:
        raise AlreadyPatchedError(
            "Good news: this ISO already has the current Archipelago "
            "patch. You can play it in Dolphin as it is — no need to "
            "patch it again."
        )
    if state == DOL_OLD:
        raise OutdatedPatchError(
            "This ISO was patched with an older version of the Gotcha "
            "Force apworld. Please select your clean, unpatched USA ISO "
            'instead: the patcher will create or refresh the " [AP]" '
            "copy next to it with the current patch. Your save files "
            "are not affected."
        )
    if state != DOL_VANILLA:
        raise IsoPatchError(_MSG_UNEXPECTED)
    sections = _dol_header(dol)
    if sections.offsets[dol_patch.FREE_SECTION] or sections.sizes[dol_patch.FREE_SECTION]:
        raise IsoPatchError(_MSG_UNEXPECTED)
    if len(dol) != _dol_size(dol) or len(dol) % ALIGN:
        raise IsoPatchError(_MSG_UNEXPECTED)


def _dol_patch_state(dol: bytes) -> str:
    sections = _dol_header(dol)
    word = _read_word(dol, _marker_hook_file_offset(dol))
    if word == dol_patch.MARKER_HOOK_VANILLA:
        return DOL_VANILLA
    if word != dol_patch.MARKER_HOOK_PATCHED:
        return DOL_UNEXPECTED
    offset, address, size = (sections.offsets[dol_patch.FREE_SECTION],
                             sections.addresses[dol_patch.FREE_SECTION],
                             sections.sizes[dol_patch.FREE_SECTION])
    if address != dol_patch.LOAD_ADDR or size != len(dol_patch.ZONE) or dol[offset:offset + size] != dol_patch.ZONE:
        return DOL_OLD
    for patch_address, _vanilla, patched in dol_patch.OTHER_HOOK_WORDS:
        patch_offset = _file_offset_of_ram_address(dol, patch_address)
        if patch_offset is None or _read_word(dol, patch_offset) != patched:
            return DOL_OLD
    return DOL_CURRENT


def _read_word(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + WORD_SIZE], "big")

def _file_offset_of_ram_address(header: bytes, address: int) -> int | None:
    """Used to find where in the DOL a specific byte in a RAM Address is.

    It gives the offset. To find where it is in the ISO, add dol_offset to it.
    Returns None if no section of the game holds it.
    """
    sections = _dol_header(header)
    for offset, load_address, size in zip(sections.offsets, sections.addresses, sections.sizes, strict=True):
        if size and load_address != dol_patch.LOAD_ADDR and load_address <= address < load_address + size:
            return offset + (address - load_address)
    return None

def _marker_hook_file_offset(header: bytes) -> int:
    """Same as _file_offset_of_ram_address, but for our marker hook"""
    offset = _file_offset_of_ram_address(header, dol_patch.MARKER_HOOK_ADDR)
    if offset is None:
        raise IsoPatchError(_MSG_UNEXPECTED)
    return offset

def _align(value: int, alignment: int = ALIGN) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def _first_file_offset(fst: bytes) -> int:
    if len(fst) < FST_ENTRY_LEN:
        raise IsoPatchError(_MSG_DAMAGED)
    entry_count = _read_word(fst, FST_ROOT_ENTRY_COUNT_OFF)
    minimum = None
    for index in range(1, entry_count):
        entry = fst[index * FST_ENTRY_LEN:(index + 1) * FST_ENTRY_LEN]
        if len(entry) < FST_ENTRY_LEN:
            break
        if entry[FST_ENTRY_TYPE_OFF] == FST_FILE_ENTRY:
            offset = _read_word(entry, FST_FILE_OFFSET_OFF)
            minimum = offset if minimum is None else min(minimum, offset)
    if minimum is None:
        raise IsoPatchError(_MSG_DAMAGED)
    return minimum


def default_output(src: str) -> str:
    root, ext = os.path.splitext(src)
    return root + AP_SUFFIX + ext


def _write_patched_copy(src: str, dst: str, disc: Disc, new_dol: bytes, new_fst_offset: int) -> None:
    try:
        if not os.path.exists(dst):
            shutil.copyfile(src, dst)
        with open(dst, "r+b") as f:
            f.seek(disc.dol_offset)
            f.write(new_dol)
            f.seek(new_fst_offset)
            f.write(disc.fst)
            f.seek(BOOT_FST_OFFSET)
            f.write(struct.pack(">I", new_fst_offset))
    except OSError as e:
        raise IsoPatchError(f"Could not write the patched copy:\n{e}") from e


def verify_iso(dst: str) -> bool:
    try:
        with open(dst, "rb") as f:
            boot = f.read(BOOT_LEN)
            if len(boot) < BOOT_LEN or boot[:len(dol_patch.GAME_ID)] != dol_patch.GAME_ID:
                return False
            dol_offset, fst_offset, fst_size, _ = BOOT_RECORD.unpack_from(boot, BOOT_DOL_OFFSET)
            f.seek(dol_offset)
            header = f.read(DOL_HEADER_LEN)
            if len(header) < DOL_HEADER_LEN:
                return False
            sections = _dol_header(header)
            if (sections.addresses[dol_patch.FREE_SECTION] != dol_patch.LOAD_ADDR
                    or sections.sizes[dol_patch.FREE_SECTION] != len(dol_patch.ZONE)):
                return False
            f.seek(dol_offset + sections.offsets[dol_patch.FREE_SECTION])
            if f.read(sections.sizes[dol_patch.FREE_SECTION]) != dol_patch.ZONE:
                return False
            f.seek(dol_offset + _marker_hook_file_offset(header))
            if int.from_bytes(f.read(WORD_SIZE), "big") != dol_patch.MARKER_HOOK_PATCHED:
                return False
            if fst_offset < dol_offset + _dol_size(header):
                return False
            f.seek(fst_offset)
            fst = f.read(fst_size)
            if len(fst) != fst_size or _first_file_offset(fst) < fst_offset + fst_size:
                return False
        return True
    except (OSError, IsoPatchError, struct.error, ValueError):
        return False


def patch_status_in_memory(
        read: Callable[[int, int], bytes | None]
) -> PatchStatus:
    words: dict[int, bool | None] = {}
    for address, vanilla, patched in ALL_HOOK_WORDS:
        raw = read(address, WORD_SIZE)
        if raw is None or len(raw) != WORD_SIZE:
            words[address] = None
            continue
        words[address] = _word_state(int.from_bytes(raw, "big"), vanilla, patched)
    marker = words[dol_patch.MARKER_HOOK_ADDR]
    if marker is None:
        return PatchStatus(None, words)
    if marker is False:
        return PatchStatus(PATCH_NONE, words)
    if any(w is not True for w in words.values()):
        return PatchStatus(PATCH_OLD, words)
    for lo, hi in dol_patch.PATCH_CODE_RANGES:
        raw = read(lo, hi - lo)
        if raw is None or len(raw) != hi - lo:
            return PatchStatus(None, words)
        if raw != dol_patch.ZONE[lo - dol_patch.LOAD_ADDR:hi - dol_patch.LOAD_ADDR]:
            return PatchStatus(PATCH_OLD, words)
    return PatchStatus(PATCH_CURRENT, words)


def _word_state(value: int, vanilla: int, patched: int) -> bool | None:
    if value == patched:
        return True
    if value == vanilla:
        return False
    return None
