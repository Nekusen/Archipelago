from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, Final

from BaseClasses import Item, ItemClassification
from Options import OptionError

from .data.borgs import BORGS, G_RED, NEO_G_RED, NEVER_IN_POOL
from .data.chapters import CHAPTERS
from .data.companions import COMPANIONS, KOTARO, KOTARO_UPGRADE_LADDER, UPGRADE_LADDER
from .data.zones import ZONES
from .game import GAME_NAME
from .options import GotchaForceOptions

if TYPE_CHECKING:
    from .world import GotchaForceWorld

ITEM_ID_BASE: Final = 690_000_000

STORY_KEY_ID: Final = 1
GF_CAP_ID: Final = 2
GOTCHA_BOX_ID: Final = 3
G_RED_ID: Final = 4
DEATH_CRYSTAL_ID: Final = 5
CMD_UPGRADE_ID: Final = 6
FILLER_XP_ID: Final = 9

AREA_ACCESS_ID_OFFSET: Final = 10
COMMANDER_ID_OFFSET: Final = 30
COMMANDER_UPGRADE_ID_OFFSET: Final = 60
BORG_ID_OFFSET: Final = 100_000
FRAGMENT_ID_OFFSET: Final = 200_000

PROG_STORY_KEY: Final = "Progressive Story Key"
PROG_GF_CAP: Final = "Progressive GF Energy Cap"
GOTCHA_BOX: Final = "Gotcha Box"
PROG_G_RED: Final = "Progressive G Red"
DEATH_CRYSTAL: Final = "Death Crystal"
PROG_CMD_UPGRADE: Final = "Progressive Commander Upgrade"
FILLER_XP: Final = "Borg Experience"

GF_CAP_STEPS: Final = (600, 1000, 1500, 2000, 2500, 3000, 3500)
GF_CAP_COUNT: Final = len(GF_CAP_STEPS)
G_RED_COUNT: Final = 2
CMD_UPGRADE_COUNT: Final = len(UPGRADE_LADDER)

MIN_PIECES_FOR_FRAGMENTS: Final = 2

COMMANDER_LADDERS: Final = {i: (KOTARO_UPGRADE_LADDER if i == KOTARO else UPGRADE_LADDER) for i in COMPANIONS}
COMMANDER_UPGRADE_STEPS: Final = {i: len(ladder) for i, ladder in COMMANDER_LADDERS.items()}


class GotchaForceItem(Item):
    game = GAME_NAME


def _build_tables() -> tuple[dict[str, int], dict[str, ItemClassification]]:
    ids: dict[str, int] = {
        PROG_STORY_KEY: ITEM_ID_BASE + STORY_KEY_ID,
        PROG_GF_CAP: ITEM_ID_BASE + GF_CAP_ID,
        GOTCHA_BOX: ITEM_ID_BASE + GOTCHA_BOX_ID,
        PROG_G_RED: ITEM_ID_BASE + G_RED_ID,
        DEATH_CRYSTAL: ITEM_ID_BASE + DEATH_CRYSTAL_ID,
        PROG_CMD_UPGRADE: ITEM_ID_BASE + CMD_UPGRADE_ID,
        FILLER_XP: ITEM_ID_BASE + FILLER_XP_ID,
    }
    cls: dict[str, ItemClassification] = {
        PROG_STORY_KEY: ItemClassification.progression,
        PROG_GF_CAP: ItemClassification.progression,
        GOTCHA_BOX: ItemClassification.progression,
        PROG_G_RED: ItemClassification.progression,
        DEATH_CRYSTAL: ItemClassification.progression_skip_balancing,
        PROG_CMD_UPGRADE: ItemClassification.useful,
        FILLER_XP: ItemClassification.filler,
    }
    for tile in ZONES:
        ids[area_access_item_name(tile)] = ITEM_ID_BASE + AREA_ACCESS_ID_OFFSET + tile
        cls[area_access_item_name(tile)] = ItemClassification.progression
    for idx in COMPANIONS:
        ids[commander_item_name(idx)] = ITEM_ID_BASE + COMMANDER_ID_OFFSET + idx
        cls[commander_item_name(idx)] = ItemClassification.progression
        ids[commander_upgrade_item_name(idx)] = ITEM_ID_BASE + COMMANDER_UPGRADE_ID_OFFSET + idx
        cls[commander_upgrade_item_name(idx)] = ItemClassification.useful
    for borg_id, borg in BORGS.items():
        ids[borg.name] = ITEM_ID_BASE + BORG_ID_OFFSET + borg_id
        cls[borg.name] = ItemClassification.useful
        ids[fragment_item_name(borg_id)] = ITEM_ID_BASE + FRAGMENT_ID_OFFSET + borg_id
        cls[fragment_item_name(borg_id)] = ItemClassification.useful
    return ids, cls


def area_access_item_name(tile: int) -> str:
    return f"Area Access - {ZONES[tile]}"


def commander_item_name(idx: int) -> str:
    return f"Commander - {COMPANIONS[idx]}"


def commander_upgrade_item_name(idx: int) -> str:
    return f"Progressive Commander Upgrade - {COMPANIONS[idx]}"


def fragment_item_name(borg_id: int) -> str:
    return f"{BORGS[borg_id].name} Fragment"


ITEM_NAME_TO_ID, ITEM_CLASSIFICATION = _build_tables()

ITEM_NAME_GROUPS: dict[str, set[str]] = {
    "Story Keys": {PROG_STORY_KEY},
    "GF Energy Caps": {PROG_GF_CAP},
    "Death Crystals": {DEATH_CRYSTAL},
    "Area Access": {area_access_item_name(t) for t in ZONES},
    "Commanders": {commander_item_name(i) for i in COMPANIONS},
    "Commander Upgrades": ({commander_upgrade_item_name(i) for i in COMPANIONS} | {PROG_CMD_UPGRADE}),
    "Borgs": {b.name for b in BORGS.values()},
    "Borg Fragments": {fragment_item_name(i) for i in BORGS},
}


def create_all_items(world: GotchaForceWorld) -> None:
    opts = world.options
    pool = _progression_pool(world)
    fragments = uses_fragments(opts)

    promoted = list(world.progression_borgs)
    for borg_id in promoted:
        pool += borg_pool_items(borg_id, fragments)

    unfilled = len(world.multiworld.get_unfilled_locations(world.player))
    free_slots = unfilled - len(pool)
    if free_slots < 0 and promoted:
        free_slots = _trim_promoted_borgs(world, pool, promoted, free_slots, fragments)
    if free_slots < 0:
        free_slots = _drop_spare_crystals(world, pool, free_slots)
    if free_slots < 0:
        raise OptionError(
            f"Gotcha Force: {len(pool)} fixed items for {unfilled} "
            f"locations; the pool does not fit. With a very early goal "
            f"(goal_mission) the seed has few missions: raise "
            f"mission_checks, enable gacha_locations, choose a deeper "
            f"goal or require fewer Death Crystals"
        )

    if opts.gacha_locations:
        pool += _borg_items_that_fit(world, promoted, free_slots, fragments)

    pool += [FILLER_XP] * (unfilled - len(pool))

    world.multiworld.itempool += [create_item(world, n) for n in pool]


def _progression_pool(world: GotchaForceWorld) -> list[str]:
    opts = world.options
    pool: list[str] = []
    pool += [PROG_STORY_KEY] * _story_key_count(world)
    pool += [PROG_GF_CAP] * GF_CAP_COUNT
    if not world.box_unlocked:
        pool.append(GOTCHA_BOX)
    pool += [PROG_G_RED] * (G_RED_COUNT - g_red_steps(world.starting_borg))
    pool += [DEATH_CRYSTAL] * world.crystals_in_pool
    if opts.area_access_items:
        for tile in sorted(_zones_in_seed(world)):
            if tile not in world.start_areas:
                pool.append(area_access_item_name(tile))
    pool += [commander_item_name(idx) for idx in COMPANIONS]
    if opts.commander_items == opts.commander_items.option_individual:
        for idx in COMPANIONS:
            pool += [commander_upgrade_item_name(idx)] * COMMANDER_UPGRADE_STEPS[idx]
    else:
        pool += [PROG_CMD_UPGRADE] * CMD_UPGRADE_COUNT
    return pool


def _story_key_count(world: GotchaForceWorld) -> int:
    return max(world.keys_map.values(), default=0)


def g_red_steps(starting_borg: int) -> int:
    return {G_RED: 1, NEO_G_RED: 2}.get(starting_borg, 0)


def _zones_in_seed(world: GotchaForceWorld) -> set[int]:
    return {CHAPTERS[c].tile for c in world.chapters_in_pool} | {CHAPTERS[c].tile for c in world.goal_chapters}


def uses_fragments(options: GotchaForceOptions) -> bool:
    return options.borg_items == options.borg_items.option_fragments


def borg_pool_items(borg_id: int, fragments_mode: bool) -> list[str]:
    n = BORGS[borg_id].fragments
    if fragments_mode and n >= MIN_PIECES_FOR_FRAGMENTS:
        return [fragment_item_name(borg_id)] * n
    return [BORGS[borg_id].name]


def _trim_promoted_borgs(
    world: GotchaForceWorld, pool: list[str], promoted: list[int], free_slots: int, fragments: bool
) -> int:
    unfilled = len(pool) + free_slots
    trimmable = _trimmable_promoted_borgs(world, promoted, fragments)
    world.random.shuffle(trimmable)
    removed: list[int] = []
    while free_slots < 0 and trimmable:
        borg = trimmable.pop()
        for name in borg_pool_items(borg, fragments):
            pool.remove(name)
            free_slots += 1
        promoted.remove(borg)
        removed.append(borg)
    world.progression_borgs = tuple(sorted(promoted))
    world.progression_borg_items = borg_pool_item_names(promoted, fragments)
    logging.warning(
        "Gotcha Force (%s): the pool did not fit; %d fewer progression borg(s) (%s) so that it fits in %d locations",
        world.player_name,
        len(removed),
        ", ".join(BORGS[b].name for b in removed),
        unfilled,
    )
    return free_slots


def _trimmable_promoted_borgs(world: GotchaForceWorld, promoted: list[int], fragments: bool) -> list[int]:
    early = world.multiworld.local_early_items[world.player]
    protected = set(world.achievement_borg_items)
    return [
        b
        for b in promoted
        if borg_pool_items(b, fragments)[0] not in early and borg_pool_items(b, fragments)[0] not in protected
    ]


def borg_pool_item_names(borg_ids: Iterable[int], fragments_mode: bool) -> set[str]:
    return {name for borg_id in borg_ids for name in borg_pool_items(borg_id, fragments_mode)}


def _drop_spare_crystals(world: GotchaForceWorld, pool: list[str], free_slots: int) -> int:
    spare = world.crystals_in_pool - world.options.death_crystals_required.value
    dropped = min(spare, -free_slots)
    if dropped > 0:
        for _ in range(dropped):
            pool.remove(DEATH_CRYSTAL)
        free_slots += dropped
        world.crystals_in_pool -= dropped
        logging.warning(
            "Gotcha Force (%s): the pool did not fit; %d fewer Death Crystal(s), %d left for the %d required",
            world.player_name,
            dropped,
            world.crystals_in_pool,
            world.options.death_crystals_required.value,
        )
    return free_slots


def _borg_items_that_fit(world: GotchaForceWorld, promoted: list[int], free_slots: int, fragments: bool) -> list[str]:
    order = sorted(set(BORGS) - NEVER_IN_POOL - set(promoted) - set(world.box_borgs))
    world.random.shuffle(order)
    borg_pool: list[str] = []
    for borg_id in order:
        borg_items = borg_pool_items(borg_id, fragments)
        if len(borg_pool) + len(borg_items) > free_slots:
            continue
        borg_pool += borg_items
    return borg_pool


def create_item(world: GotchaForceWorld, name: str) -> GotchaForceItem:
    return GotchaForceItem(name, _borg_classification(world, name), ITEM_NAME_TO_ID[name], world.player)


def _borg_classification(world: GotchaForceWorld, name: str) -> ItemClassification:
    if name in world.achievement_borg_items:
        return ItemClassification.progression
    if name in world.progression_borg_items:
        return ItemClassification.progression_deprioritized_skip_balancing
    return ITEM_CLASSIFICATION[name]
