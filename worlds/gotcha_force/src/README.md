# Source of the DOL patch

This folder is the readable form of the code patch that `iso_patch.py` applies
to the `main.dol` of Gotcha Force (USA, `GG4E08`): a new text section (`text2`,
loaded at `0x80001810`) holding PowerPC routines and their data tables, and a
few game instructions rewritten to jump into it (the hooks). What each routine
does and why is in the header of its `.s` file.

None of this ships: the folder is left out of the `.apworld` (see `.apignore`).
What reaches players is `data/dol_patch.py`, kept by hand from what these
sources build, so the world runs on the standard library alone.

## Building

From the package root, after `pip install -r src/requirements.txt` (keystone, the assembler):

```
python src/build_patch.py                  # compare with data/dol_patch.py and print what to copy there
python src/build_patch.py --iso GAME.iso   # also check the hooks and the free room against a clean USA ISO
python src/build_patch.py --all            # print every value, changed or not
```

It writes nothing. It builds the section image, compares every value with
`data/dol_patch.py` and prints, ready to paste, the ones that differ: the image
(`_ZONE_B64`), its size, the hook words, the code ranges. Paste them over the
old ones and run it again until it says the module is up to date.

## Files

| File | Content |
|---|---|
| `build_patch.py` | The entry point. |
| `hooks.py` | The list to edit: every routine (its `.s` and its address) and every hook (site, vanilla word, `b` or `bl`, routine). |
| `addresses.py` | Every address and value with a name: the game routines the patch calls, the hook sites and their vanilla words, the layout of the section and the values baked into its tables. |
| `asm/*.s` | One routine per file, PowerPC syntax as keystone reads it plus the conventions below. |
| `layout.py` | The data tables of the section, the ranges the client compares, and the image: every block at its address, checked against overlaps. |
| `assembler.py` | Expands the conventions, assembles a routine at its address, refuses branches that leave it, and computes the hook words. |

## Adding a hook

1. In Ghidra or the Dolphin debugger, find the instruction to replace: its
   address and its 4-byte word.
2. `addresses.py`: name that address, that word and the address of the new
   routine: free room in the section (the map below shows the gaps) or after
   the last block, moving `ZONE_END`. A routine placed after `0x800025C0` is
   already inside the ranges the client compares.
3. `asm/<routine>.s`: write the routine, with the header every routine has
   (`in` and `note` only when they say something):

   ```
   # <name>: what it does, in one line
   # hook : <HOOK_SITE>, by b or bl    (was: <the instruction it replaces>)
   # load : <ROUTINE_ADDRESS>
   # in   : registers it reads on entry
   # uses : registers it changes
   # note : what the code does not show
   ```

   Entered by `bl`, it ends with `blr`; entered by `b`, it jumps back itself.
   If the game still needs the instruction the hook overwrites, the routine
   runs it.
4. `hooks.py`: add one `Routine` and one `Hook`, at the end of `OTHER_HOOKS`.
5. If the routine reads a value the client writes (a new mailbox): its
   starting value in `layout.py` (`_client_table_defaults`) and its address in
   `data/addresses.py`, where the client takes it from.
6. `python src/build_patch.py --iso <clean ISO>`: fix what it reports, paste
   what it prints into `data/dol_patch.py`, run it again until up to date.
7. Patch your ISO again. Any change to the patch makes existing `[AP]` copies
   "older", and the client asks their players to patch again.

## Map of the section

| Address | Size | Block | Written at runtime by |
|---|---|---|---|
| `0x80001810` | 212 B | `counter_create`: target of the map screen hook; creates the 35 digit objects once, then performs the displaced call | |
| `0x80001910` | 900 B | `counter_update`: per-frame callback of every digit; reads `AP_TABLE`, places and frames the glyph, tints the row icon from `AP_FLAGS` | |
| `0x80001F00` | 80 B | frame floats 0..19 (10..19 are the yellow glyphs, used when X == Y) | |
| `0x80001F50` | 28 B | slot floats -3..3 | |
| `0x80001F70` | 16 B | x offset, glyph spacing, y offset, scale | |
| `0x80001F80` | 24 B | tints: done, out of logic, vanilla (selected/unselected each) | the client (the first four) |
| `0x80001F98` | 2 B | `AP_STORY_BORG`: borg id deployed while the Gotcha Box is not owned; starts as G Red | the client |
| `0x80001F9A` | 1 B | `AP_GACHA_SUPPRESS`: 1 = the game grants no reward; starts at 0 | the client |
| `0x80001F9B` | 1 B | `AP_GACHA_CREDIT`: 1 = kills by the player's side fill the gacha meter; starts at 0 | the client |
| `0x80001FA0` | 12 B | `story_borg`: loads the id from `AP_STORY_BORG` | |
| `0x80002000` | 512 B | `AP_TABLE`: (done, total) per chapter; starts at zero, so the counters are hidden | the client |
| `0x80002200` | 256 B | `AP_FLAGS`: bit0 completed, bit1 out of logic, per chapter; starts at zero | the client |
| `0x80002300` | 700 B | descriptors of the 35 digit objects | |
| `0x800025C0` | 44 B | `gacha_suppress`: stub in place of the first instruction of the reward dispatch | |
| `0x80002600` | 128 B | `counter_standalone`: callable variant of `counter_create`, for debugging | |
| `0x80002700` | 152 B | `icon_tint`: tints the row icon inside the game's own color writes, so a cursor move never shows the vanilla color for a frame | |
| `0x80002800` | 60 B | `gacha_credit`: gate of the gacha meter that also accepts kills by the player's team | |
| `0x80002840` | | end of the section | |

The gaps are zero. The three ranges the client compares to recognise the
patch version (`PATCH_CODE_RANGES`) are `0x80001810..0x80001F80`,
`0x80001FA0..0x80002000` and `0x800025C0..0x80002840`: code and baked
constants only.

## Hooks

| Address | Was | Now | Routine |
|---|---|---|---|
| `0x801A71F4` | `bl 0x801A73D4` (last call of the map screen init) | `b counter_create` | `counter_create` performs the displaced call itself |
| `0x8017FF60` | `li r26, 0x615` (story borg id) | `bl story_borg` | `story_borg` |
| `0x801CEBE0` | `stwu r1, -0x20(r1)` (first instruction of the reward dispatch) | `b gacha_suppress` | `gacha_suppress` re-executes it on the vanilla path |
| `0x801AA434` | `bl sprite_set_color` (row color on a cursor move) | `bl icon_tint` | `icon_tint` tail-jumps to `sprite_set_color` |
| `0x801AA67C` | `bl sprite_set_color` (row color while blinking) | `bl icon_tint` | idem |
| `0x8002F244` | `lbz r0, 0x3e6(r28)` (gate of the gacha meter) | `bl gacha_credit` | `gacha_credit` |

These six instructions are the only bytes of the game the patch rewrites;
each `.s` file quotes the one it replaces (`was:`).

## Conventions of the `.s` files

keystone reads plain PowerPC syntax (numeric registers, `#` comments,
local labels). On top of it, `assembler.py` resolves four forms before
assembling, all with names from `addresses.py`:

- `hi(NAME)` and `lo(NAME)`: the halves of an address for `lis` + `addi`
  or `lis` + a load/store displacement, with the usual sign adjustment.
- `$NAME`: the value of a constant as an immediate (`li 3, $OBJ_TYPE_HUD`).
- `call NAME` and `jump NAME`: a call or a jump to an absolute address,
  expanded to `lis r12 / addi r12 / mtctr r12 / bctrl` (or `bctr`).

Each file is assembled on its own at its load address, so labels are local
to a routine.

### Why `call` and `jump` instead of `bl` and `b`

keystone can encode `bl <absolute address>` with a wrong target and report
no error. Every call and jump that leaves a routine therefore goes through
the count register, and `assembler.py` refuses any `b`, `bl` or conditional
branch whose target is outside its block. The relative branches the hooks
themselves need are computed from the addresses (`branch_word` in
`assembler.py`), never assembled.
