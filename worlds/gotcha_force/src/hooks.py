"""What the patch adds to the game: the routines of the new section and the game instructions that jump to them.

To add a hook: name its addresses in addresses.py, write its routine in asm/, then add one Routine and one
Hook below. `python src/build_patch.py` prints what changes in data/dol_patch.py.
"""

from typing import Final, NamedTuple

import addresses


class Routine(NamedTuple):
    """One routine of the new section: its source file in asm/ and the address it is assembled at."""
    source: str
    address: int


class Hook(NamedTuple):
    """One rewritten game instruction: where, its vanilla word, `bl` (link) or `b`, and the routine it jumps to."""
    site: int
    vanilla: int
    link: bool
    target: int


#: every routine of the new section (the data tables are placed by layout.py)
ROUTINES: Final = (
    Routine("counter_create.s", addresses.COUNTER_CREATE),
    Routine("counter_update.s", addresses.COUNTER_UPDATE),
    Routine("story_borg.s", addresses.STORY_BORG_ROUTINE),
    Routine("gacha_suppress.s", addresses.GACHA_SUPPRESS_ROUTINE),
    Routine("counter_standalone.s", addresses.COUNTER_STANDALONE),
    Routine("icon_tint.s", addresses.ICON_TINT_ROUTINE),
    Routine("gacha_credit.s", addresses.GACHA_CREDIT_ROUTINE),
)

#: the map screen hook; its word is also what tells whether a DOL or a running game is patched
MARKER_HOOK: Final = Hook(addresses.MARKER_HOOK_ADDR, addresses.MARKER_HOOK_VANILLA, link=False,
                          target=addresses.COUNTER_CREATE)

#: the other hooks, in the order data/dol_patch.py lists them (a new one goes at the end)
OTHER_HOOKS: Final = (
    Hook(addresses.STORY_BORG_HOOK, addresses.STORY_BORG_VANILLA, link=True,
         target=addresses.STORY_BORG_ROUTINE),
    Hook(addresses.GACHA_GRANT_HOOK, addresses.GACHA_GRANT_VANILLA, link=False,
         target=addresses.GACHA_SUPPRESS_ROUTINE),
    Hook(addresses.ICON_TINT_HOOK_CURSOR, addresses.ICON_TINT_VANILLA_CURSOR, link=True,
         target=addresses.ICON_TINT_ROUTINE),
    Hook(addresses.ICON_TINT_HOOK_BLINK, addresses.ICON_TINT_VANILLA_BLINK, link=True,
         target=addresses.ICON_TINT_ROUTINE),
    Hook(addresses.GACHA_CREDIT_HOOK, addresses.GACHA_CREDIT_VANILLA, link=True,
         target=addresses.GACHA_CREDIT_ROUTINE),
)
