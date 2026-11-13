"""The new section of the DOL: every routine and data table at its address, and the image they make together."""

import struct
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import addresses
from assembler import assemble
from hooks import ROUTINES

ASM_DIR: Final = Path(__file__).resolve().parent / "asm"

#: stretches nothing writes at runtime (code and baked constants): the client compares them with the
#: image to recognise the patch version; the tables it fills and the descriptors stay out
CODE_RANGES: Final = (
    (addresses.COUNTER_CREATE, addresses.AP_TINTS),
    (addresses.STORY_BORG_ROUTINE, addresses.AP_TABLE),
    (addresses.GACHA_SUPPRESS_ROUTINE, addresses.ZONE_END),
)


@dataclass(frozen=True)
class Block:
    """One piece of the section image."""
    name: str
    addr: int
    data: bytes
    code: bool

    @property
    def end(self) -> int:
        return self.addr + len(self.data)


def symbols() -> dict[str, int]:
    """Every integer constant of addresses.py, for the asm sources."""
    return {name: value for name, value in vars(addresses).items()
            if name.isupper() and isinstance(value, int)}


def routine_name(source: str) -> str:
    return Path(source).stem


def code_blocks() -> list[Block]:
    """Every routine of hooks.ROUTINES assembled at its address."""
    symbol_table = symbols()
    return [Block(routine_name(routine.source), routine.address,
                  assemble((ASM_DIR / routine.source).read_text(encoding="utf-8"), routine.address,
                           symbol_table, routine_name(routine.source)),
                  code=True)
            for routine in ROUTINES]


def _floats(values: Iterable[float]) -> bytes:
    return b"".join(struct.pack(">f", float(value)) for value in values)


def _words(values: Iterable[int]) -> bytes:
    return b"".join(struct.pack(">I", value) for value in values)


def _digit_descriptors() -> bytes:
    """One ui object descriptor per glyph.

    The digit animation, the index that encodes row and glyph, a starting position:
    counter_update rewrites x and y every frame, so the position only has to be valid.
    """
    return b"".join(
        struct.pack(">IIfff", addresses.DIGIT_ANIM, addresses.descriptor_index(row, glyph),
                    addresses.DESC_X0 + addresses.DESC_DX * glyph,
                    addresses.DESC_Y0 + addresses.DESC_DY * row, addresses.DESC_Z)
        for row in range(addresses.ROWS) for glyph in range(addresses.GLYPHS_PER_ROW)
    )


def _client_table_defaults() -> list[Block]:
    """The tables the client fills, at their vanilla values.

    Without a client the game deploys G Red, grants rewards and counts only
    the player's kills, as it always did.
    """
    return [
        Block("story_borg_default", addresses.AP_STORY_BORG,
              struct.pack(">H", addresses.STORY_BORG_VANILLA_ID), code=False),
        Block("gacha_suppress_default", addresses.AP_GACHA_SUPPRESS, addresses.SWITCH_OFF, code=False),
        Block("gacha_credit_default", addresses.AP_GACHA_CREDIT, addresses.SWITCH_OFF, code=False),
        Block("ap_table", addresses.AP_TABLE, bytes(addresses.AP_TABLE_SIZE), code=False),
        Block("ap_flags", addresses.AP_FLAGS, bytes(addresses.AP_FLAGS_SIZE), code=False),
    ]


def data_blocks() -> list[Block]:
    """The baked constants the routines read, the client tables and the glyph descriptors."""
    frames = _floats(range(addresses.GLYPH_FRAMES))
    slots = _floats(range(addresses.SLOT_MIN, addresses.SLOT_MAX + 1))
    layout = _floats((addresses.X_OFFSET_VALUE, addresses.DIGIT_SPACING_VALUE,
                      addresses.Y_OFFSET_VALUE, addresses.DIGIT_SCALE_VALUE))
    tints = _words((addresses.TINT_DONE_SELECTED, addresses.TINT_DONE_UNSELECTED,
                    addresses.TINT_OUT_OF_LOGIC_SELECTED, addresses.TINT_OUT_OF_LOGIC_UNSELECTED,
                    addresses.TINT_VANILLA_SELECTED, addresses.TINT_VANILLA_UNSELECTED))
    return [
        Block("frame_floats", addresses.FRAME_FLOATS, frames, code=False),
        Block("slot_floats", addresses.SLOT_FLOATS, slots, code=False),
        Block("layout_floats", addresses.X_OFFSET, layout, code=False),
        Block("tints", addresses.AP_TINTS, tints, code=False),
        *_client_table_defaults(),
        Block("digit_descriptors", addresses.DIGIT_DESCRIPTORS, _digit_descriptors(), code=False),
    ]


def blocks() -> list[Block]:
    """Every block of the section, by address; an overlap or a block past ZONE_END is an error."""
    out = sorted(code_blocks() + data_blocks(), key=lambda block: block.addr)
    previous = None
    for block in out:
        if block.addr < addresses.LOAD_ADDR:
            raise ValueError(f"{block.name} at {block.addr:#x} starts before the section ({addresses.LOAD_ADDR:#x})")
        if previous is not None and block.addr < previous.end:
            raise ValueError(f"{block.name} at {block.addr:#x} overlaps {previous.name}, "
                             f"which runs until {previous.end:#x}")
        if block.end > addresses.ZONE_END:
            raise ValueError(f"{block.name} ends at {block.end:#x}, past ZONE_END ({addresses.ZONE_END:#x}): "
                             f"move ZONE_END in addresses.py")
        previous = block
    return out


def zone_image() -> bytes:
    """The section image: every block at its offset, zero elsewhere."""
    image = bytearray(addresses.ZONE_SIZE)
    for block in blocks():
        offset = block.addr - addresses.LOAD_ADDR
        image[offset:offset + len(block.data)] = block.data
    return bytes(image)
