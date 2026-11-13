from __future__ import annotations

from typing import Final

from .. import slot_keys
from ..data.borgs import BORGS
from ..data.chapters import CHAPTERS
from ..data.companions import COMPANIONS
from ..data.zones import ZONES
from ..items import (
    CMD_UPGRADE_COUNT,
    COMMANDER_UPGRADE_STEPS,
    G_RED_COUNT,
    GF_CAP_COUNT,
)
from ..logic import progression
from ..options import GotchaBox
from . import logic, tracker
from .logic import COMMANDER_INDIVIDUAL, ApState, SlotData
from .tracker import (
    GO_MODE_GREEN,
    LINE_HAVE,
    LINE_INFO,
    LINE_MISSING,
    InventoryGroup,
)

G_RED_CHAIN: Final = ("none yet", "G Red", "Neo G Red")

PROGRESS_FOLD: Final = "progress"
ZONES_FOLD: Final = "zones"
COMMANDERS_FOLD: Final = "commanders"
BORGS_FOLD: Final = "borgs"


def inventory_groups(
    ap_state: ApState,
    slot: SlotData,
    found: int,
    total: int,
) -> list[InventoryGroup]:
    groups = [
        InventoryGroup(PROGRESS_FOLD, "Progress", open=True, lines=tuple(progress_lines(ap_state, slot, found, total)))
    ]
    zones = zone_group(ap_state, slot)
    if zones is not None:
        groups.append(zones)
    groups.append(commander_group(ap_state, slot))
    groups.append(borg_group(ap_state, slot))
    return groups


def progress_lines(
    ap_state: ApState,
    slot: SlotData,
    found: int,
    total: int,
) -> list[tuple[int, str]]:
    goal = " / ".join(tracker.chapter_label(c) for c in logic.slot_value(slot, slot_keys.GOAL_CHAPTERS))
    lines = [(LINE_INFO, f"Goal: {goal}"), (LINE_INFO, f"Checks found: {count_text(found, total)}")]
    needed = logic.slot_value(slot, slot_keys.DEATH_CRYSTALS_REQUIRED)
    in_pool = logic.slot_value(slot, slot_keys.DEATH_CRYSTALS_IN_POOL)
    pool_note = f" ({in_pool} in the pool)" if in_pool else ""
    lines.append((LINE_INFO, f"Death Crystals: {count_text(ap_state.crystals, needed)} needed{pool_note}"))
    keys = story_keys_total(slot)
    lines.append(
        (LINE_INFO, f"Story Keys: {count_text(ap_state.story_keys, keys)}" if keys else "Story Keys: none in this seed")
    )
    lines.append((LINE_INFO, _gf_cap_line(ap_state, slot)))
    lines.append(_gotcha_box_line(ap_state, slot))
    g_red = min(ap_state.g_red, G_RED_COUNT)
    lines.append((LINE_INFO, f"Progressive G Red: {count_text(g_red, G_RED_COUNT)} ({G_RED_CHAIN[g_red]})"))
    if not logic.slot_value(slot, slot_keys.AREA_ACCESS_ITEMS):
        lines.append((LINE_INFO, "Area Access: off, every zone is open"))
    return lines


def count_text(have: int, total: int) -> str:
    text = f"{have} / {total}"
    return f"[color={GO_MODE_GREEN}]{text}[/color]" if total and have >= total else text


def story_keys_total(slot: SlotData) -> int:
    return max(
        progression.keys_needed_by_chapter(
            logic.chapter_pool_for_slot(slot), logic.slot_value(slot, slot_keys.STORY_KEYS)
        ).values(),
        default=0,
    )


def _gf_cap_line(ap_state: ApState, slot: SlotData) -> str:
    starting_cost = logic.slot_value(slot, slot_keys.STARTING_BORG_COST)
    caps = min(ap_state.gf_caps, GF_CAP_COUNT)
    line = f"GF Energy Cap: {logic.gf_cap_value(ap_state, starting_cost)} ({count_text(caps, GF_CAP_COUNT)} caps"
    if caps and not ap_state.gotcha_box:
        line += f"; the logic counts {starting_cost} until the Gotcha Box"
    return f"{line})"


def _gotcha_box_line(ap_state: ApState, slot: SlotData) -> tuple[int, str]:
    if not ap_state.gotcha_box:
        return LINE_MISSING, "Gotcha Box: not yet"
    from_start = logic.slot_value(slot, slot_keys.GOTCHA_BOX) == GotchaBox.option_unlocked
    suffix = " from the start" if from_start else ""
    return LINE_HAVE, f"Gotcha Box: owned{suffix}"


def zone_group(ap_state: ApState, slot: SlotData) -> InventoryGroup | None:
    if not logic.slot_value(slot, slot_keys.AREA_ACCESS_ITEMS):
        return None
    present = {CHAPTERS[c].tile for c in logic.chapter_pool_for_slot(slot)}
    present |= {CHAPTERS[c].tile for c in logic.slot_value(slot, slot_keys.GOAL_CHAPTERS)}
    start = set(logic.slot_value(slot, slot_keys.START_AREAS))
    lines = tuple(
        (LINE_HAVE if tile in ap_state.areas else LINE_MISSING, ZONES[tile] + (" (start)" if tile in start else ""))
        for tile in sorted(present)
    )
    owned = len(present & ap_state.areas)
    return InventoryGroup(ZONES_FOLD, f"Zones ({count_text(owned, len(present))})", open=True, lines=lines)


def commander_group(ap_state: ApState, slot: SlotData) -> InventoryGroup:
    mode = logic.slot_value(slot, slot_keys.COMMANDER_ITEMS)
    individual = mode == COMMANDER_INDIVIDUAL
    levels = logic.upgrade_levels(ap_state, mode)
    recruited = logic.unlocked_partners(ap_state)
    lines: list[tuple[int, str]] = []
    if not individual:
        upgrades = min(ap_state.global_upgrades, CMD_UPGRADE_COUNT)
        lines.append((LINE_INFO, f"Commander Upgrades: {count_text(upgrades, CMD_UPGRADE_COUNT)}"))
    for commander in sorted(COMPANIONS):
        name = COMPANIONS[commander]
        detail = _upgrade_detail(ap_state, commander) if individual else ""
        if commander in recruited:
            lines.append((LINE_HAVE, f"{name} - Lv {levels[commander - 1]}{detail}"))
        else:
            lines.append((LINE_MISSING, name + detail))
    title = f"Commanders ({count_text(len(recruited), len(COMPANIONS))})"
    return InventoryGroup(COMMANDERS_FOLD, title, open=True, lines=tuple(lines))


def _upgrade_detail(ap_state: ApState, commander: int) -> str:
    steps = COMMANDER_UPGRADE_STEPS[commander]
    have = min(ap_state.commander_upgrades[commander], steps)
    return f" ({count_text(have, steps)} upgrades)"


def borg_group(ap_state: ApState, slot: SlotData) -> InventoryGroup:
    starting = logic.slot_value(slot, slot_keys.STARTING_BORG)
    box_borgs = set(logic.slot_value(slot, slot_keys.BOX_BORGS))
    complete = logic.desired_borgs(ap_state, box_borgs)
    lines = [(LINE_HAVE, f"{logic.borg_name(starting)} (starting borg)")]
    for borg_id in sorted(complete - {starting}, key=logic.borg_name):
        in_box = " (Gotcha Box)" if borg_id in box_borgs else ""
        lines.append((LINE_HAVE, logic.borg_name(borg_id) + in_box))
    pending = logic.pending_fragments(ap_state)
    lines.extend(
        (LINE_MISSING, f"{logic.borg_name(borg_id)} ({pending[borg_id]} / {BORGS[borg_id].fragments} fragments)")
        for borg_id in sorted(pending, key=logic.borg_name)
    )
    title = f"Borgs ({len(complete | {starting})}"
    if pending:
        title += f", {len(pending)} in fragments"
    return InventoryGroup(BORGS_FOLD, f"{title})", open=False, lines=tuple(lines))
