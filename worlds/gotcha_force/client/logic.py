from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Final

from .. import items, locations, slot_keys
from ..data.addresses import N_COMMANDERS, NO_ID
from ..data.borgs import BORGS, G_RED, G_RED_COST, G_RED_NAME, NEO_G_RED, NEO_G_RED_NAME
from ..data.chapters import CHAPTERS, NEO_G_RED_CHAPTER
from ..data.companions import KOTARO, KOTARO_GLOBAL_LEVELS
from ..data.rewards import REWARDS
from ..data.zones import ZONES
from ..items import (
    CMD_UPGRADE_COUNT,
    COMMANDER_LADDERS,
    DEATH_CRYSTAL,
    FILLER_XP,
    G_RED_COUNT,
    GF_CAP_STEPS,
    GOTCHA_BOX,
    ITEM_NAME_TO_ID,
    PROG_CMD_UPGRADE,
    PROG_G_RED,
    PROG_GF_CAP,
    PROG_STORY_KEY,
)
from ..locations import CHECK_CHAPTERS, LOCATION_NAME_TO_ID
from ..logic import progression
from ..logic.achievements import TRIBE_ORDER
from ..logic.enemies import MODE_VANILLA, PARTNER_VANILLA, SPECIAL_VANILLA, STAT_VANILLA
from ..logic.gacha import UNSCALED_RATE, gacha_chapters
from ..logic.progression import POOL_ALL
from ..options import (
    DIFFICULTY_RATIOS,
    UNLIMITED_RATIO,
    CommanderItems,
    EnemyAIMaximum,
    EnemyAIMinimum,
    EnemyLevelMaximum,
    EnemyLevelMinimum,
    GachaChecks,
    GachaLocations,
    GFLogicDifficulty,
    TribeForceMinCost,
)

SlotData = Mapping[str, Any]

ITEM_ID_TO_NAME = {v: k for k, v in ITEM_NAME_TO_ID.items()}
LOCATION_ID_TO_NAME = {v: k for k, v in LOCATION_NAME_TO_ID.items()}

COMMANDER_GLOBAL = CommanderItems.option_global_upgrades
COMMANDER_INDIVIDUAL = CommanderItems.option_individual

LEGACY_MISSION_CHECKS = 3

SLOT_DEFAULTS: dict[str, Any] = {
    slot_keys.GF_LOGIC_DIFFICULTY: GFLogicDifficulty.option_normal,
    slot_keys.MISSION_CHECKS: LEGACY_MISSION_CHECKS,
    slot_keys.STARTING_BORG_COST: G_RED_COST,
    slot_keys.STARTING_BORG: G_RED,
    slot_keys.TRIBE_FORCE_MIN_COST: TribeForceMinCost.default,
    slot_keys.GACHA_LOCATIONS: GachaLocations.default,
    slot_keys.GACHA_RATE: UNSCALED_RATE,
    slot_keys.GACHA_PARTNER_KILLS: True,
    slot_keys.GACHA_CHECKS: GachaChecks.option_per_fragment,
    slot_keys.COMMANDER_ITEMS: COMMANDER_GLOBAL,
    slot_keys.MISSION_POOL: POOL_ALL,
    slot_keys.VARIANT_PICKS: (),
    slot_keys.CUSTOM_CHAPTERS: (),
    slot_keys.PARTNER_LOGIC: False,
    slot_keys.START_AREAS: (),
    slot_keys.BOX_BORGS: (),
    slot_keys.PROGRESSION_BORGS: (),
    slot_keys.ACHIEVEMENTS: False,
    slot_keys.ACHIEVEMENT_TYPES: (),
    slot_keys.ACHIEVEMENT_BORGS: (),
    slot_keys.ALLY_FINISHER_CHAPTERS: (),
    slot_keys.TRIBE_FORCE_TRIBES: TRIBE_ORDER,
    slot_keys.DEATH_CRYSTALS_IN_POOL: None,
    slot_keys.GOTCHA_BOX: None,
    slot_keys.ENEMY_SEED: 0,
    slot_keys.ENEMY_RANDOMIZATION: MODE_VANILLA,
    slot_keys.COMMANDER_ACE_BORGS: SPECIAL_VANILLA,
    slot_keys.BOSS_BORGS: SPECIAL_VANILLA,
    slot_keys.PARTNER_BORGS: PARTNER_VANILLA,
    slot_keys.PARTNER_ACE_BORGS: SPECIAL_VANILLA,
    slot_keys.ENEMY_AI: STAT_VANILLA,
    slot_keys.ENEMY_AI_MINIMUM: EnemyAIMinimum.default,
    slot_keys.ENEMY_AI_MAXIMUM: EnemyAIMaximum.default,
    slot_keys.ENEMY_LEVELS: STAT_VANILLA,
    slot_keys.ENEMY_LEVEL_MINIMUM: EnemyLevelMinimum.default,
    slot_keys.ENEMY_LEVEL_MAXIMUM: EnemyLevelMaximum.default,
}

FORCE_MAX = GF_CAP_STEPS[-1]

G_RED_NAMES: Final = {G_RED: G_RED_NAME, NEO_G_RED: NEO_G_RED_NAME}

UNKNOWN_ZONE: Final = "?"

_COUNTED_ITEMS: Final = {
    PROG_STORY_KEY: "story_keys",
    PROG_GF_CAP: "gf_caps",
    PROG_G_RED: "g_red",
    DEATH_CRYSTAL: "crystals",
    PROG_CMD_UPGRADE: "global_upgrades",
    FILLER_XP: "xp_items",
}
_AREA_BY_NAME: Final = {items.area_access_item_name(tile): tile for tile in ZONES}
_COMMANDER_BY_NAME: Final = {items.commander_item_name(i): i for i in range(1, N_COMMANDERS + 1)}
_UPGRADE_BY_NAME: Final = {items.commander_upgrade_item_name(i): i for i in range(1, N_COMMANDERS + 1)}
_BORG_BY_NAME: Final = {BORGS[i].name: i for i in BORGS}
_FRAGMENT_BY_NAME: Final = {items.fragment_item_name(i): i for i in BORGS}


@dataclass
class ApState:
    story_keys: int = 0
    gf_caps: int = 0
    gotcha_box: bool = False
    g_red: int = 0
    crystals: int = 0
    areas: set[int] = field(default_factory=set)
    commanders: set[int] = field(default_factory=set)
    commander_upgrades: Counter = field(default_factory=Counter)
    global_upgrades: int = 0
    borgs: set[int] = field(default_factory=set)
    fragments: Counter = field(default_factory=Counter)
    xp_items: int = 0

    @classmethod
    def from_item_ids(cls, item_ids: Iterable[int]) -> ApState:
        state = cls()
        for item_id in item_ids:
            name = ITEM_ID_TO_NAME.get(item_id)
            if name is not None:
                state._add(name)
        return state

    def _add(self, name: str) -> None:
        if name in _COUNTED_ITEMS:
            counter = _COUNTED_ITEMS[name]
            setattr(self, counter, getattr(self, counter) + 1)
        elif name == GOTCHA_BOX:
            self.gotcha_box = True
        elif name in _AREA_BY_NAME:
            self.areas.add(_AREA_BY_NAME[name])
        elif name in _COMMANDER_BY_NAME:
            self.commanders.add(_COMMANDER_BY_NAME[name])
        elif name in _UPGRADE_BY_NAME:
            self.commander_upgrades[_UPGRADE_BY_NAME[name]] += 1
        elif name in _BORG_BY_NAME:
            self.borgs.add(_BORG_BY_NAME[name])
        elif name in _FRAGMENT_BY_NAME:
            self.fragments[_FRAGMENT_BY_NAME[name]] += 1


@dataclass(frozen=True)
class _ChapterGates:
    state: ApState
    area_on: bool
    partner_gated: bool
    recruited: set[int]

    def open(self, chapter: int) -> bool:
        if self.area_on and CHAPTERS[chapter].tile not in self.state.areas:
            return False
        if chapter == NEO_G_RED_CHAPTER and self.state.g_red < G_RED_COUNT:
            return False
        if self.partner_gated and not progression.partner_requirement_met(chapter, self.recruited):
            return False
        return True


def gf_ratio_for_slot(slot: SlotData) -> float:
    return DIFFICULTY_RATIOS.get(slot_value(slot, slot_keys.GF_LOGIC_DIFFICULTY),
                                 DIFFICULTY_RATIOS[SLOT_DEFAULTS[slot_keys.GF_LOGIC_DIFFICULTY]])


def slot_value(slot: SlotData, key: str) -> Any:
    if key not in SLOT_DEFAULTS:
        return slot[key]
    return slot.get(key, SLOT_DEFAULTS[key])


def is_empty_entry(borg_id: int) -> bool:
    return borg_id in (NO_ID, 0)


def borg_name(borg_id: int) -> str:
    if borg_id in BORGS:
        return BORGS[borg_id].name
    return G_RED_NAMES.get(borg_id, f"borg {borg_id:#06x}")


def chapter_zone_name(chapter: int) -> str:
    if chapter not in CHAPTERS:
        return UNKNOWN_ZONE
    return ZONES.get(CHAPTERS[chapter].tile, UNKNOWN_ZONE)


def companion_bits(state: ApState) -> int:
    bits = 0
    for idx in state.commanders:
        bits |= 1 << idx
    return bits


def upgrade_levels(state: ApState, mode: int) -> bytes:
    levels = bytearray(N_COMMANDERS)
    if mode == COMMANDER_GLOBAL:
        upgrades = min(state.global_upgrades, CMD_UPGRADE_COUNT)
        for commander in range(1, N_COMMANDERS + 1):
            if commander == KOTARO:
                levels[_level_index(commander)] = _ladder_level(KOTARO_GLOBAL_LEVELS, upgrades)
            else:
                levels[_level_index(commander)] = upgrades
    else:
        for commander in state.commanders:
            ladder = COMMANDER_LADDERS[commander]
            steps = min(state.commander_upgrades[commander], len(ladder))
            levels[_level_index(commander)] = _ladder_level(ladder, steps)
    return bytes(levels)


def _level_index(commander: int) -> int:
    return commander - 1


def _ladder_level(ladder: tuple[int, ...], steps: int) -> int:
    return ladder[steps - 1] if steps else 0


def desired_borgs(state: ApState,
                  box_borgs: Iterable[int] = ()) -> set[int]:
    complete = set(state.borgs)
    for borg_id, pieces in state.fragments.items():
        if pieces >= BORGS[borg_id].fragments:
            complete.add(borg_id)
    if state.g_red >= G_RED_COUNT:
        complete.add(NEO_G_RED)
    elif state.g_red == 1:
        complete.add(G_RED)
    if state.gotcha_box:
        complete.update(b for b in box_borgs if b in BORGS)
    return complete


def pending_fragments(state: ApState) -> dict[int, int]:
    return {borg_id: pieces
            for borg_id, pieces in state.fragments.items()
            if 0 < pieces < BORGS[borg_id].fragments}


def allowed_chapters(state: ApState, slot: SlotData) -> set[int]:
    gates = _ChapterGates(state, bool(slot_value(slot, slot_keys.AREA_ACCESS_ITEMS)),
                          partner_logic_on(slot), unlocked_partners(state))
    keys = progression.keys_needed_by_chapter(chapter_pool_for_slot(slot), slot_value(slot, slot_keys.STORY_KEYS))
    out = {chapter for chapter, needed in keys.items()
           if state.story_keys >= needed and gates.open(chapter)}
    if state.crystals >= slot_value(slot, slot_keys.DEATH_CRYSTALS_REQUIRED):
        out |= {chapter for chapter in slot_value(slot, slot_keys.GOAL_CHAPTERS)
                if gates.open(chapter)}
    return out


def partner_logic_on(slot: SlotData) -> bool:
    return bool(slot_value(slot, slot_keys.PARTNER_LOGIC))


def unlocked_partners(state: ApState) -> set[int]:
    return set(state.commanders)


def chapter_pool_for_slot(slot: SlotData) -> list[int]:
    return progression.chapter_pool(tuple(slot_value(slot, slot_keys.GOAL_CHAPTERS)),
                        slot_value(slot, slot_keys.MISSION_POOL),
                        slot_value(slot, slot_keys.VARIANT_PICKS),
                        slot_value(slot, slot_keys.CUSTOM_CHAPTERS))


def pending_checks_by_chapter(
        allowed: set[int], missing: set[int],
        checks: int = SLOT_DEFAULTS[slot_keys.MISSION_CHECKS],
        gacha_by_chapter: Mapping[int, set[int]] | None = None,
        ach_by_chapter: Mapping[int, set[int]] | None = None,
        ach_in_logic: set[int] | None = None,
) -> dict[int, int]:
    out: dict[int, int] = {}
    for chapter in allowed:
        pending = len(chapter_check_ids(chapter, checks, gacha_by_chapter,
                                        ach_by_chapter, ach_in_logic) & missing)
        if pending:
            out[chapter] = pending
    return out


def chapter_check_ids(chapter: int, checks: int,
                      gacha_by_chapter: Mapping[int, set[int]] | None = None,
                      ach_by_chapter: Mapping[int, set[int]] | None = None,
                      ach_in_logic: set[int] | None = None,
                      ) -> set[int]:
    out = _check_ids(chapter, checks) | _reward_ids([chapter])
    if gacha_by_chapter:
        out |= gacha_by_chapter.get(chapter, set())
    if ach_by_chapter:
        anchored = ach_by_chapter.get(chapter, set())
        out |= (anchored if ach_in_logic is None
                else anchored & ach_in_logic)
    return out


def _check_ids(chapter: int, checks: int) -> set[int]:
    if chapter not in CHECK_CHAPTERS:
        return set()
    return {LOCATION_NAME_TO_ID[locations.check_location_name(chapter, check_number)]
            for check_number in range(1, checks + 1)}


def _reward_ids(chapters: Iterable[int]) -> set[int]:
    won = set(chapters)
    return {LOCATION_NAME_TO_ID[reward.name] for reward in REWARDS
            if any(c in won for c in reward.triggers)}


def chapters_in_logic_for_slot(state: ApState, slot: SlotData, allowed: set[int],
                      chapter_costs: Mapping[int, int],
                      ratio: float) -> set[int]:
    starting_cost = slot_value(slot, slot_keys.STARTING_BORG_COST)
    cap = gf_cap_value(state, starting_cost) if state.gotcha_box else starting_cost
    return chapters_in_logic(allowed, chapter_costs, ratio, cap)


def gf_cap_value(state: ApState, starting_cost: int) -> int:
    if state.gf_caps <= 0:
        return starting_cost
    step = GF_CAP_STEPS[min(state.gf_caps, len(GF_CAP_STEPS)) - 1]
    return max(starting_cost, step)


def chapters_in_logic(allowed: set[int], chapter_costs: Mapping[int, int],
                      ratio: float, gf_cap: int) -> set[int]:
    if ratio == UNLIMITED_RATIO:
        return set(allowed)
    return {c for c in allowed
            if _fits(chapter_costs.get(c, 0), ratio, gf_cap)}


def _fits(cost: int, ratio: float, available: float) -> bool:
    return available >= FORCE_MAX or cost <= ratio * available


def gacha_by_chapter_map(assignments: Mapping[int, int | None],
                         slot: SlotData,
                         extra: Mapping[int, Iterable[int]] | None = None,
                         ) -> dict[int, set[int]]:
    chapters = chapter_pool_for_slot(slot)
    by_borg = gacha_location_map(assignments, slot, extra)
    out: dict[int, set[int]] = {}
    for borg_id, borg_chapters in gacha_chapters(assignments, chapters, extra).items():
        ids = by_borg.get(borg_id)
        if not ids:
            continue
        for chapter in borg_chapters:
            out.setdefault(chapter, set()).update(ids)
    return out


def gacha_location_map(assignments: Mapping[int, int | None],
                       slot: SlotData,
                       extra: Mapping[int, Iterable[int]] | None = None,
                       ) -> dict[int, list[int]]:
    chapters = chapter_pool_for_slot(slot)
    whole = bool(slot_value(slot, slot_keys.GACHA_CHECKS))
    out: dict[int, list[int]] = {}
    for borg_id in sorted(gacha_chapters(assignments, chapters, extra)):
        out[borg_id] = [LOCATION_NAME_TO_ID[n]
                        for n in locations.gacha_locations_for(borg_id, whole)]
    return out


def won_location_ids(victories: Mapping[int, int],
                     checks: int = SLOT_DEFAULTS[slot_keys.MISSION_CHECKS]) -> set[int]:
    won = won_chapters(victories)
    out: set[int] = set()
    for chapter in won:
        out |= _check_ids(chapter, checks)
    return out | _reward_ids(won)


def won_chapters(victories: Mapping[int, int]) -> set[int]:
    return {chapter for chapter, wins in victories.items() if wins > 0}


def goal_reached(victories: Mapping[int, int], slot: SlotData) -> bool:
    return bool(won_chapters(victories) & set(slot_value(slot, slot_keys.GOAL_CHAPTERS)))


def go_mode(in_logic: set[int], slot: SlotData) -> bool:
    return any(c in in_logic for c in slot_value(slot, slot_keys.GOAL_CHAPTERS))
