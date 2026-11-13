#!/usr/bin/env python3
"""Build the DOL patch from src/ and show what data/dol_patch.py must hold.

Usage, from the package root (needs `pip install keystone-engine`):

  python src/build_patch.py                # compare with data/dol_patch.py and print what to copy there
  python src/build_patch.py --all          # print every value, changed or not
  python src/build_patch.py --iso GAME.iso # also check the hooks and the free room against a clean USA ISO

Nothing is written: copy by hand what the report marks as CHANGED. Exit code 0 when
data/dol_patch.py is up to date (and the ISO, if given, is fine), 1 otherwise.
"""

import argparse
import base64
import importlib.util
import struct
import sys
from pathlib import Path
from types import ModuleType
from typing import Final, NamedTuple

SRC: Final = Path(__file__).resolve().parent
DATA_MODULE: Final = SRC.parent / "data" / "dol_patch.py"
sys.path.insert(0, str(SRC))

import addresses  # noqa: E402
import hooks  # noqa: E402
import layout  # noqa: E402
from assembler import branch_word  # noqa: E402

B64_LINE_WIDTH: Final = 64
MISSING: Final = object()


class Value(NamedTuple):
    """One value of data/dol_patch.py: its label, what src/ builds, what the module holds and the lines to paste."""
    label: str
    built: object
    shipped: object
    text: str


# ------------------------------------------------------------------ what src/ builds

def hook_word(hook: hooks.Hook) -> int:
    """The new word of a hook: the `b` or `bl` from its site to its routine."""
    return branch_word(hook.site, hook.target, hook.link)


def routine_at(address: int) -> str:
    names = [layout.routine_name(r.source) for r in hooks.ROUTINES if r.address == address]
    return names[0] if names else f"{address:#010x} (no routine there!)"


def hook_comment(hook: hooks.Hook) -> str:
    return f"{'bl' if hook.link else 'b'} {routine_at(hook.target)}"


def _tuple_lines(name: str, rows: list[tuple[str, str]]) -> str:
    body = "\n".join(f"    {row},{f'  # {comment}' if comment else ''}" for row, comment in rows)
    return f"{name}: Final = (\n{body}\n)"


def _b64_text(image: bytes) -> str:
    text = base64.b64encode(image).decode("ascii")
    lines = "\n".join(f'    "{text[i:i + B64_LINE_WIDTH]}"' for i in range(0, len(text), B64_LINE_WIDTH))
    return f"_ZONE_B64 = (\n{lines}\n)"


def built_values(image: bytes, shipped: ModuleType) -> list[Value]:
    marker = hooks.MARKER_HOOK
    marker_words = (marker.site, marker.vanilla, hook_word(marker))
    other_words = tuple((h.site, h.vanilla, hook_word(h)) for h in hooks.OTHER_HOOKS)

    def get(name: str) -> object:
        return getattr(shipped, name, MISSING)

    return [
        Value("GAME_ID", addresses.GAME_ID, get("GAME_ID"),
              f'GAME_ID: Final = b"{addresses.GAME_ID.decode("ascii")}"'),
        Value("FREE_SECTION", addresses.FREE_SECTION, get("FREE_SECTION"),
              f"FREE_SECTION: Final = {addresses.FREE_SECTION}"),
        Value("LOAD_ADDR", addresses.LOAD_ADDR, get("LOAD_ADDR"),
              f"LOAD_ADDR: Final = {addresses.LOAD_ADDR:#010x}"),
        Value("ZONE_SIZE", len(image), get("ZONE_SIZE"),
              f"ZONE_SIZE: Final = {len(image):#x}            # bytes of the section image"),
        Value("MARKER_HOOK_*", marker_words,
              (get("MARKER_HOOK_ADDR"), get("MARKER_HOOK_VANILLA"), get("MARKER_HOOK_PATCHED")),
              f"MARKER_HOOK_ADDR: Final = {marker.site:#010x}      # last bl of the map screen init\n"
              f"MARKER_HOOK_VANILLA: Final = {marker.vanilla:#010x}   # original word at MARKER_HOOK_ADDR\n"
              f"MARKER_HOOK_PATCHED: Final = {hook_word(marker):#010x}   # {hook_comment(marker)}"),
        Value("OTHER_HOOK_WORDS", other_words, _as_tuple(get("OTHER_HOOK_WORDS")),
              _tuple_lines("OTHER_HOOK_WORDS",
                           [(f"({h.site:#010x}, {h.vanilla:#010x}, {hook_word(h):#010x})", hook_comment(h))
                            for h in hooks.OTHER_HOOKS])),
        Value("PATCH_CODE_RANGES", layout.CODE_RANGES, _as_tuple(get("PATCH_CODE_RANGES")),
              _tuple_lines("PATCH_CODE_RANGES",
                           [(f"({low:#010x}, {high:#010x})", "") for low, high in layout.CODE_RANGES])),
        Value("_ZONE_B64", image, get("ZONE"), _b64_text(image)),
    ]


def _as_tuple(value: object) -> object:
    return tuple(tuple(row) for row in value) if isinstance(value, (tuple, list)) else value


# ------------------------------------------------------------------ the report

def load_shipped() -> ModuleType | str:
    """data/dol_patch.py executed by path, or the error that stopped it (a bad paste, for example)."""
    try:
        spec = importlib.util.spec_from_file_location("shipped_dol_patch", DATA_MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:  # any error of the module (a bad paste) is reported, not raised
        return f"{type(e).__name__}: {e}"
    return module


def change_note(value: Value) -> str:
    if value.shipped is MISSING or (isinstance(value.shipped, tuple) and MISSING in value.shipped):
        return "MISSING in data/dol_patch.py"
    if value.label == "OTHER_HOOK_WORDS" and len(value.built) != len(value.shipped):
        return f"CHANGED ({len(value.built) - len(value.shipped):+d} hook(s))"
    return "CHANGED"


def report(values: list[Value], show_all: bool) -> bool:
    """Print the comparison and the lines to paste; return True when data/dol_patch.py is up to date."""
    width = max(len(v.label) for v in values)
    print("data/dol_patch.py compared with what src/ builds:\n")
    changed = [v for v in values if v.built != v.shipped]
    for value in values:
        print(f"  {value.label:<{width}}  {'same' if value not in changed else change_note(value)}")
    to_print = values if show_all else changed
    if not to_print:
        print("\ndata/dol_patch.py is up to date: nothing to copy.")
        return True
    print("\nCopy into data/dol_patch.py, replacing what is there:" if changed else "\nEvery value:")
    for value in to_print:
        print(f"\n----- {value.label} -----\n{value.text}")
    return not changed


# ------------------------------------------------------------------ the --iso check

BOOT_LEN: Final = 0x440
BOOT_DOL_OFFSET: Final = 0x420
DOL_HEADER_LEN: Final = 0xE4
DOL_SECTIONS: Final = 18
FST_ENTRY_LEN: Final = 12
ALIGN: Final = 0x20


def check_iso(path: str, image: bytes) -> bool:
    """Check a clean USA ISO: the vanilla word of every hook, an empty text2 and room for the bigger DOL."""
    print(f"\nChecking {path}:")
    with open(path, "rb") as f:
        boot = f.read(BOOT_LEN)
        dol_offset, fst_offset, fst_size, _ = struct.unpack_from(">4I", boot, BOOT_DOL_OFFSET)
        f.seek(dol_offset)
        header = f.read(DOL_HEADER_LEN)
        offsets = struct.unpack_from(f">{DOL_SECTIONS}I", header, 0x00)
        loads = struct.unpack_from(f">{DOL_SECTIONS}I", header, 0x48)
        sizes = struct.unpack_from(f">{DOL_SECTIONS}I", header, 0x90)
        dol_size = max(o + s for o, s in zip(offsets, sizes, strict=True) if s)
        f.seek(dol_offset)
        dol = f.read(dol_size)
        f.seek(fst_offset)
        fst = f.read(fst_size)
    ok = True
    if boot[:len(addresses.GAME_ID)] != addresses.GAME_ID:
        print(f"  game id {boot[:6]!r}, expected {addresses.GAME_ID!r}: not the USA disc")
        return False
    if sizes[addresses.FREE_SECTION]:
        print(f"  text{addresses.FREE_SECTION} is not empty: this ISO is already patched, use the clean one")
        return False
    for hook in (hooks.MARKER_HOOK, *hooks.OTHER_HOOKS):
        offset = next((o + hook.site - a for o, a, s in zip(offsets, loads, sizes, strict=True)
                       if s and a <= hook.site < a + s), None)
        label = f"  {hook.site:#010x} ({routine_at(hook.target)})"
        if offset is None:
            print(f"{label}: no section of the DOL holds this address")
            ok = False
            continue
        word = int.from_bytes(dol[offset:offset + 4], "big")
        if word == hook.vanilla:
            print(f"{label}: vanilla word ok")
        else:
            print(f"{label}: the game has {word:#010x}, addresses.py says {hook.vanilla:#010x}")
            ok = False
    first_file = min(struct.unpack_from(">I", fst, i * FST_ENTRY_LEN + 4)[0]
                     for i in range(1, struct.unpack_from(">I", fst, 8)[0])
                     if fst[i * FST_ENTRY_LEN] == 0)
    fst_end = ((dol_offset + dol_size + len(image) + ALIGN - 1) & ~(ALIGN - 1)) + fst_size
    if fst_end <= first_file:
        print(f"  room: the moved FST ends {first_file - fst_end:#x} bytes before the first game file: ok")
    else:
        print(f"  room: the moved FST would run {fst_end - first_file:#x} bytes into the first game file")
        ok = False
    return ok


# ------------------------------------------------------------------ entry point

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--all", action="store_true", help="print every value, changed or not")
    parser.add_argument("--iso", help="a clean USA ISO to check the hooks and the free room against")
    args = parser.parse_args()

    try:
        image = layout.zone_image()
    except Exception as e:  # an error of the sources is reported, not raised
        print(f"ERROR building the patch: {e}")
        return 1
    shipped = load_shipped()
    if isinstance(shipped, str):
        print(f"data/dol_patch.py does not load ({shipped}); every value follows.\n")
        shipped = ModuleType("empty")
    up_to_date = report(built_values(image, shipped), args.all)
    iso_ok = check_iso(args.iso, image) if args.iso else True
    return 0 if up_to_date and iso_ok else 1


if __name__ == "__main__":
    sys.exit(main())
