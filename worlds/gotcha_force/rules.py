from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any, Final, NamedTuple

from BaseClasses import ItemClassification
from rule_builder.rules import Has, Rule, True_

from . import items, locations
from .data.achievements import STYLES, THEME_CHAPTERS, TRIBES
from .data.chapters import CHAPTERS, NEO_G_RED_CHAPTER
from .data.companions import COMPANIONS
from .data.spawns import SIGNATURE_BORGS
from .items import (
    DEATH_CRYSTAL,
    G_RED_COUNT,
    GF_CAP_STEPS,
    GOTCHA_BOX,
    PROG_G_RED,
    PROG_GF_CAP,
    PROG_STORY_KEY,
    GotchaForceItem,
)
from .locations import GotchaForceLocation
from .logic import achievements, progression
from .logic.achievements import ChapterSpec, CommanderChapterSpec, CommanderSpec, Spec, TribeSpec
from .logic.progression import PARTNER_CHOICE, PARTNER_FIXED
from .regions import GOAL_ARENA_REGION, GOAL_GATE_ENTRANCE

if TYPE_CHECKING:
    from .world import GotchaForceWorld

EVENT_VICTORY: Final = "Victory"
GOAL_EVENT_LOCATION: Final = "Goal Mission"

COMFORTABLE_START: Final = 8

FORCE_EDITOR_RATIO: Final = 1.0

ChapterRules = dict[int, Rule]


class OpeningPlan(NamedTuple):
    items: list[str]
    fits: bool


def opening_items(world: GotchaForceWorld,
                  taken: int) -> OpeningPlan | None:
    owned = Counter(item.name for item in
                    world.multiworld.precollected_items[world.player])
    room = locations.starting_spots(world, _open_chapters(world, owned)) - taken
    opening: list[str] = []
    spent = 0
    fits = True
    while True:
        opened = _open_chapters(world, owned)
        closed = [c for c in world.keys_map if c not in opened]
        free = locations.starting_spots(world, opened) - taken - spent
        if not closed or free >= COMFORTABLE_START:
            return OpeningPlan(opening, fits)
        asks = sorted({tuple(chapter_missing_items(world, c, owned))
                       for c in closed}, key=lambda a: (len(a), a))
        buy = _widest_opening(world, owned, asks)
        if len(buy) > free:
            return None
        fits = fits and spent + len(buy) <= room
        if fits:
            opening += buy
        spent += len(buy)
        owned.update(buy)


def _open_chapters(world: GotchaForceWorld,
                   owned: Counter[str]) -> set[int]:
    return {c for c in world.keys_map
            if not chapter_missing_items(world, c, owned)}


def chapter_missing_items(world: GotchaForceWorld, chapter: int,
                          owned: Counter[str]) -> list[str]:
    opts = world.options
    missing = [PROG_STORY_KEY] * (world.keys_map.get(chapter, 0)
                                  - owned[PROG_STORY_KEY])
    zone = items.area_access_item_name(CHAPTERS[chapter].tile)
    if opts.area_access_items and not owned[zone]:
        missing.append(zone)
    needed = gf_cap_items_needed(world.chapter_costs.get(chapter, 0),
                                 world.gf_ratio, world.starting_borg_cost)
    if needed:
        if not owned[GOTCHA_BOX]:
            missing.append(GOTCHA_BOX)
        missing += [PROG_GF_CAP] * (needed - owned[PROG_GF_CAP])
    if chapter == NEO_G_RED_CHAPTER:
        missing += [PROG_G_RED] * (G_RED_COUNT - owned[PROG_G_RED])
    eligible = progression.eligible_partners(chapter)
    if eligible and not any(owned[items.commander_item_name(i)] for i in eligible):
        missing.append(items.commander_item_name(_seed_rotated_partner(eligible, world.enemy_seed)))
    return missing


def gf_cap_items_needed(cost: int, ratio: float, starting_cost: int) -> int:
    if cost <= ratio * starting_cost:
        return 0
    for needed, step in enumerate(GF_CAP_STEPS, start=1):
        if cost <= ratio * max(starting_cost, step):
            return needed
    return len(GF_CAP_STEPS)


def _seed_rotated_partner(eligible: Iterable[int], seed: int) -> int:
    return min(eligible, key=lambda i: (i - seed) % len(COMPANIONS))


def _widest_opening(world: GotchaForceWorld, owned: Counter[str],
                    asks: list[tuple[str, ...]]) -> tuple[str, ...]:
    cheapest = [a for a in asks if len(a) == len(asks[0])]
    return max(cheapest, key=lambda a: locations.starting_spots(
        world, _open_chapters(world, owned + Counter(a))
    ))


def goal_items(world: GotchaForceWorld) -> frozenset[str]:
    names = {DEATH_CRYSTAL, GOTCHA_BOX, PROG_GF_CAP, PROG_G_RED}
    names.update(items.area_access_item_name(CHAPTERS[chapter].tile)
                 for chapter in world.goal_chapters)
    return frozenset(names)


def create_goal_event(world: GotchaForceWorld) -> None:
    _make_event(world, GOAL_ARENA_REGION, GOAL_EVENT_LOCATION, EVENT_VICTORY)


def _make_event(world: GotchaForceWorld, region_name: str,
                location_name: str, item_name: str) -> None:
    region = world.get_region(region_name)
    loc = GotchaForceLocation(world.player, location_name, None, region)
    loc.place_locked_item(GotchaForceItem(
        item_name, ItemClassification.progression, None, world.player
    ))
    region.locations.append(loc)


def set_all_rules(world: GotchaForceWorld) -> None:
    chapter_rules = {chapter: chapter_rule(world, chapter) for chapter in world.chapters_in_pool}
    _set_check_rules(world, chapter_rules)
    _set_reward_rules(world, chapter_rules)
    _set_gacha_rules(world, chapter_rules)
    _set_achievement_rules(world, chapter_rules)
    world.set_rule(world.get_entrance(GOAL_GATE_ENTRANCE), goal_rule(world))
    world.set_completion_rule(Has(EVENT_VICTORY))


def chapter_rule(world: GotchaForceWorld, chapter: int) -> Rule:
    parts: list[Rule] = []
    keys = world.keys_map.get(chapter, 0)
    if keys:
        parts.append(Has(PROG_STORY_KEY, count=keys))
    return _all(parts + _access_parts(world, chapter))


def _all(parts: list[Rule]) -> Rule:
    if not parts:
        return True_()
    rule = parts[0]
    for part in parts[1:]:
        rule = rule & part
    return rule


def _access_parts(world: GotchaForceWorld, chapter: int) -> list[Rule]:
    parts: list[Rule] = []
    if world.options.area_access_items:
        parts.append(Has(items.area_access_item_name(CHAPTERS[chapter].tile)))
    cap_rule = _gf_rule(world, world.chapter_costs.get(chapter, 0))
    if cap_rule is not None:
        parts.append(cap_rule)
    if chapter == NEO_G_RED_CHAPTER:
        parts.append(Has(PROG_G_RED, count=G_RED_COUNT))
    partner = _partner_rule(chapter)
    if partner is not None:
        parts.append(partner)
    return parts


def _gf_rule(world: GotchaForceWorld, cost: int) -> Rule | None:
    needed = gf_cap_items_needed(cost, world.gf_ratio, world.starting_borg_cost)
    if needed == 0:
        return None
    return Has(GOTCHA_BOX) & Has(PROG_GF_CAP, count=needed)


def _partner_rule(chapter: int) -> Rule | None:
    eligible = progression.eligible_partners(chapter)
    if not eligible:
        return None
    return _any([Has(items.commander_item_name(i)) for i in sorted(eligible)])


def _any(parts: list[Rule]) -> Rule:
    rule = parts[0]
    for part in parts[1:]:
        rule = rule | part
    return rule


def _set_check_rules(world: GotchaForceWorld, chapter_rules: ChapterRules) -> None:
    for chapter, rule in chapter_rules.items():
        for check_number in range(1, world.options.mission_checks.value + 1):
            world.set_rule(world.get_location(locations.check_location_name(chapter, check_number)), rule)


def _set_reward_rules(world: GotchaForceWorld, chapter_rules: ChapterRules) -> None:
    for reward in locations.pool_rewards(world):
        world.set_rule(world.get_location(reward.name), _missions_rule(chapter_rules, reward.triggers))


def _missions_rule(chapter_rules: ChapterRules, chapters: Iterable[int]) -> Rule:
    return _any([chapter_rules[c] for c in chapters])


def _set_gacha_rules(world: GotchaForceWorld, chapter_rules: ChapterRules) -> None:
    whole = locations.gacha_only_one_per_borg(world)
    for borg_id, chapters in world.gacha_chapters.items():
        rule = _missions_rule(chapter_rules, sorted(chapters))
        for name in locations.gacha_locations_for(borg_id, whole):
            world.set_rule(world.get_location(name), rule)


def _set_achievement_rules(world: GotchaForceWorld, chapter_rules: ChapterRules) -> None:
    for spec in world.achievement_plan.specs:
        world.set_rule(world.get_location(locations.achievement_location_name(spec)),
                       achievement_rule(world, chapter_rules, spec))


def achievement_rule(world: GotchaForceWorld, chapter_rules: ChapterRules,
                     spec: Spec) -> Rule:
    spec = achievements.as_spec(spec)
    if spec.kind not in _ACHIEVEMENT_PARTS:
        raise ValueError(spec)
    parts: list[Rule] = [] if spec.kind in achievements.BOX_FREE_TYPES else [Has(GOTCHA_BOX)]
    return _all(parts + _ACHIEVEMENT_PARTS[spec.kind](world, chapter_rules, spec))


def _partner_style_parts(world: GotchaForceWorld, chapter_rules: ChapterRules,
                         spec: CommanderSpec) -> list[Rule]:
    deployable = achievements.deployable_chapters(spec.commander, chapter_rules.keys())
    fixed = [c for c in deployable if CHAPTERS[c].partner_mode in PARTNER_FIXED]
    eligible = [c for c in deployable if CHAPTERS[c].partner_mode == PARTNER_CHOICE]
    ways: list[Rule] = []
    if fixed:
        ways.append(_missions_rule(chapter_rules, fixed))
    if eligible:
        ways.append(Has(items.commander_item_name(spec.commander)) & _missions_rule(chapter_rules, eligible))
    return [_any(ways), *_style_parts(world, chapter_rules, STYLES[spec.commander])]


def _style_parts(world: GotchaForceWorld, chapter_rules: ChapterRules,
                 tribes: Iterable[str]) -> list[Rule]:
    style = _style_rule(world, chapter_rules, tribes)
    return [] if style is None else [style]


def _style_rule(world: GotchaForceWorld, chapter_rules: ChapterRules,
                tribes: Iterable[str]) -> Rule | None:
    wanted = set(tribes)
    if TRIBES.get(world.starting_borg) in wanted:
        return None
    if any(TRIBES.get(b) in wanted for b in world.box_borgs):
        return None
    if world.options.gacha_locations:
        candidates = sorted(b for b in world.progression_borgs
                            if TRIBES.get(b) in wanted)
        return _any([_borg_complete(world, b) for b in candidates])
    chapters = achievements.farm_chapters(tuple(wanted), chapter_rules.keys(), world.enemy_assignments)
    return _any([chapter_rules[c] for c in chapters])


def _borg_complete(world: GotchaForceWorld, borg_id: int) -> Rule:
    its = items.borg_pool_items(borg_id, items.uses_fragments(world.options))
    return Has(its[0], count=len(its))


def _commander_style_parts(world: GotchaForceWorld, chapter_rules: ChapterRules,
                           spec: CommanderSpec) -> list[Rule]:
    rivals = achievements.rival_chapters(spec.commander, chapter_rules.keys())
    return [_missions_rule(chapter_rules, rivals), *_style_parts(world, chapter_rules, STYLES[spec.commander])]


def _commander_style_all_parts(world: GotchaForceWorld, chapter_rules: ChapterRules,
                               spec: CommanderChapterSpec) -> list[Rule]:
    return [chapter_rules[spec.chapter], *_style_parts(world, chapter_rules, STYLES[spec.commander])]


def _theme_parts(world: GotchaForceWorld, chapter_rules: ChapterRules,
                 spec: ChapterSpec) -> list[Rule]:
    return [chapter_rules[spec.chapter], *_style_parts(world, chapter_rules, (THEME_CHAPTERS[spec.chapter],))]


def _anchored_parts(_world: GotchaForceWorld, chapter_rules: ChapterRules,
                    spec: ChapterSpec) -> list[Rule]:
    return [chapter_rules[spec.chapter]]


def _ace_duel_parts(world: GotchaForceWorld, chapter_rules: ChapterRules,
                    spec: CommanderSpec) -> list[Rule]:
    ace = SIGNATURE_BORGS[spec.commander]
    parts = [_missions_rule(chapter_rules, achievements.rival_chapters(spec.commander, chapter_rules.keys()))]
    if ace == world.starting_borg or ace in world.box_borgs:
        return parts
    if world.options.gacha_locations:
        return [*parts, _borg_complete(world, ace)]
    sources = achievements.chapters_with_id(ace, chapter_rules.keys(), world.enemy_assignments)
    return [*parts, _missions_rule(chapter_rules, sources)]


def _tribe_force_parts(world: GotchaForceWorld, chapter_rules: ChapterRules,
                       spec: TribeSpec) -> list[Rule]:
    minimum = world.options.tribe_force_min_cost.value
    parts: list[Rule] = []
    caps_needed = gf_cap_items_needed(minimum, FORCE_EDITOR_RATIO, world.starting_borg_cost)
    if caps_needed:
        parts.append(Has(PROG_GF_CAP, count=caps_needed))
    if world.options.gacha_locations:
        witnesses = achievements.tribe_force_witnesses(
            spec.tribe, world.starting_borg, world.box_borgs,
            world.achievement_plan.achievement_borgs, minimum
        )
        return parts + [_borg_complete(world, b) for b in witnesses]
    witness_chapters = achievements.tribe_force_witness_chapters(
        spec.tribe, chapter_rules.keys(), world.enemy_assignments,
        world.starting_borg, world.box_borgs, minimum
    )
    return parts + [chapter_rules[c] for c in witness_chapters]


_ACHIEVEMENT_PARTS: dict[str, Callable[[GotchaForceWorld, ChapterRules, Any], list[Rule]]] = {
    achievements.TYPE_PARTNER_STYLE: _partner_style_parts,
    achievements.TYPE_COMMANDER_STYLE: _commander_style_parts,
    achievements.TYPE_COMMANDER_STYLE_ALL: _commander_style_all_parts,
    achievements.TYPE_THEME: _theme_parts,
    achievements.TYPE_ALLY_FINISHER: _anchored_parts,
    achievements.TYPE_NO_CASUALTIES: _anchored_parts,
    achievements.TYPE_ACE_DUEL: _ace_duel_parts,
    achievements.TYPE_TRIBE_FORCE: _tribe_force_parts,
}


def goal_rule(world: GotchaForceWorld) -> Rule:
    variants = [_all(_access_parts(world, chapter)) for chapter in world.goal_chapters]
    return (Has(DEATH_CRYSTAL,
                count=world.options.death_crystals_required.value)
            & _any(variants))
