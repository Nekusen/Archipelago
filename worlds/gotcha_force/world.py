from __future__ import annotations

import random
from collections import Counter
from collections.abc import Collection, Iterable, Mapping
from typing import Any, ClassVar, NamedTuple

from BaseClasses import Item, Location, Tutorial
from Options import OptionError
from typing_extensions import override
from worlds.AutoWorld import WebWorld, World

from . import items, locations, regions, rules, slot_keys
from .data.borgs import BORGS, COSTS, G_RED, G_RED_COST, NEVER_IN_POOL, RANDOMIZABLE
from .data.chapters import CHAPTERS
from .data.zones import STARTING_TILE
from .game import GAME_NAME
from .logic import achievements, enemies, gacha, progression
from .options import (
    DIFFICULTY_RATIOS,
    OPTION_GROUPS,
    STARTING_BORG_MIN_COST,
    UNLIMITED_RATIO,
    GotchaForceOptions,
    validate_options,
)

SLOT_DATA_VERSION = 1

ENEMY_SEED_BITS = 48

MIN_START_CHAPTERS = 3

INITIAL_BOX_BORG_COUNT = 2
PROGRESSION_BORG_SHARE = 4
EARLY_BORGS = 2
EARLY_BORGS_WITH_MORE_CHECKS = 3
MORE_CHECKS_FROM = 2

PLACED_LAST = 0
PLACED_ANYWHERE = 1
PLACED_FIRST = 2

OPTIONS_IN_SLOT = (
    slot_keys.GOAL,
    slot_keys.GACHA_LOCATIONS,
    slot_keys.GACHA_PARTNER_KILLS,
    slot_keys.GACHA_RATE,
    slot_keys.GACHA_CHECKS,
    slot_keys.MISSION_CHECKS,
    slot_keys.MISSION_POOL,
    slot_keys.STORY_KEYS,
    slot_keys.DEATH_CRYSTALS_IN_POOL,
    slot_keys.DEATH_CRYSTALS_REQUIRED,
    slot_keys.BORG_ITEMS,
    slot_keys.COMMANDER_ITEMS,
    slot_keys.AREA_ACCESS_ITEMS,
    slot_keys.GOTCHA_BOX,
    slot_keys.GF_LOGIC_DIFFICULTY,
    slot_keys.ENEMY_RANDOMIZATION,
    slot_keys.COMMANDER_ACE_BORGS,
    slot_keys.BOSS_BORGS,
    slot_keys.PARTNER_BORGS,
    slot_keys.PARTNER_ACE_BORGS,
    slot_keys.ENEMY_AI,
    slot_keys.ENEMY_AI_MINIMUM,
    slot_keys.ENEMY_AI_MAXIMUM,
    slot_keys.ENEMY_LEVELS,
    slot_keys.ENEMY_LEVEL_MINIMUM,
    slot_keys.ENEMY_LEVEL_MAXIMUM,
)

TrackerSlot = dict | None


class _AchievementInputs(NamedTuple):
    types: tuple[str, ...]
    gacha_on: bool
    min_cost: int
    tribes: tuple[str, ...]
    rng: random.Random | None
    forced_borgs: tuple[int, ...]
    forced_ally_chapters: tuple[int, ...]


class GotchaForceWeb(WebWorld):
    option_groups = OPTION_GROUPS
    tutorials = [Tutorial(  # noqa: RUF012
        "Multiworld Setup Guide",
        "A guide to setting up Gotcha Force for Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["Nekusen"],
    )]


class GotchaForceWorld(World):
    """Gotcha Force: recruit an army of Gotcha Borgs and drive the Death Force
    off the Earth. This randomizer plays over the story mode: every mission
    you beat sends checks, and the borgs, partners, map zones and story keys
    that unlock new missions arrive from the multiworld."""

    game: ClassVar[str] = GAME_NAME
    web = GotchaForceWeb()
    options_dataclass = GotchaForceOptions
    options: GotchaForceOptions  # pyright: ignore[reportIncompatibleVariableOverride]

    item_name_to_id = items.ITEM_NAME_TO_ID
    location_name_to_id = locations.LOCATION_NAME_TO_ID
    item_name_groups = items.ITEM_NAME_GROUPS
    location_name_groups = locations.LOCATION_NAME_GROUPS

    enemy_seed: int
    enemy_plan: enemies.EnemyPlan
    enemy_assignments: Mapping[int, int | None]
    chapter_costs: dict[int, int]
    gacha_chapters: dict[int, set[int]]
    gf_ratio: float
    goal_chapters: tuple[int, ...]
    mission_pool: int
    custom_chapters: tuple[int, ...]
    variant_picks: tuple[int, ...]
    chapters_in_pool: tuple[int, ...]
    keys_map: dict[int, int]
    crystals_in_pool: int
    starting_borg: int
    starting_borg_cost: int
    start_areas: set[int]
    progression_borgs: tuple[int, ...]
    progression_borg_items: Collection[str] = frozenset()
    box_borgs: tuple[int, ...]
    box_unlocked: bool
    tribe_force_tribes: tuple[str, ...]
    achievement_plan: achievements.AchievementPlan
    achievement_borg_items: Collection[str] = frozenset()

    @override
    def generate_early(self) -> None:
        opts = self.options
        validate_options(opts, self.player_name)
        self.gf_ratio = DIFFICULTY_RATIOS[opts.gf_logic_difficulty.value]
        tracker_slot = self._tracker_slot()
        self._plan_enemies(opts, tracker_slot)
        self._plan_missions(opts, tracker_slot)
        self._plan_gacha(opts)
        in_logic = self._pick_starting_borg(opts, tracker_slot)
        self._pick_box_borgs(opts, tracker_slot)
        self._plan_achievements(opts, tracker_slot)
        self._pick_start_areas(opts, tracker_slot, in_logic)
        self._push_starting_kit()
        self._plan_progression_borgs(opts, tracker_slot)
        if tracker_slot is None:
            self._plan_early_items(opts)

    def _tracker_slot(self) -> TrackerSlot:
        passthrough = getattr(self.multiworld, "re_gen_passthrough", None)
        if isinstance(passthrough, dict):
            return passthrough.get(self.game)
        return None

    def _plan_enemies(self, opts: GotchaForceOptions, tracker_slot: TrackerSlot) -> None:
        if tracker_slot is not None:
            self.enemy_seed = int(tracker_slot[slot_keys.ENEMY_SEED])
        else:
            self.enemy_seed = self.random.getrandbits(ENEMY_SEED_BITS)
        self.enemy_plan = enemies.plan_enemies(
            self.enemy_seed, opts.enemy_randomization.value,
            opts.commander_ace_borgs.value, opts.boss_borgs.value
        )
        self.enemy_assignments = self.enemy_plan.assignments
        self.chapter_costs = enemies.chapter_costs(
            self.enemy_assignments, self.enemy_plan.inserts
        )

    def _plan_missions(self, opts: GotchaForceOptions, tracker_slot: TrackerSlot) -> None:
        if tracker_slot is not None:
            self._restore_missions(tracker_slot)
            story_keys = int(tracker_slot[slot_keys.STORY_KEYS])
        else:
            self._draw_missions(opts)
            story_keys = opts.story_keys.value
        self.chapters_in_pool = tuple(
            progression.chapter_pool(self.goal_chapters, self.mission_pool, self.variant_picks, self.custom_chapters)
        )
        self.keys_map = progression.keys_needed_by_chapter(self.chapters_in_pool, story_keys)
        self.crystals_in_pool = opts.death_crystals_in_pool.value

    def _restore_missions(self, tracker_slot: dict) -> None:
        self.goal_chapters = tuple(int(c) for c in tracker_slot[slot_keys.GOAL_CHAPTERS])
        self.mission_pool = int(tracker_slot.get(slot_keys.MISSION_POOL, progression.POOL_ALL))
        self.variant_picks = tuple(int(c) for c in tracker_slot.get(slot_keys.VARIANT_PICKS, ()))
        self.custom_chapters = tuple(int(c) for c in tracker_slot.get(slot_keys.CUSTOM_CHAPTERS, ()))

    def _draw_missions(self, opts: GotchaForceOptions) -> None:
        self.goal_chapters = self._draw_goal_chapters(opts)
        self.mission_pool = opts.mission_pool.value
        plando = self._plando_chapters(opts)
        self.variant_picks = progression.pick_variants(
            self.goal_chapters, self.mission_pool, self.random, plando
        )
        if self.mission_pool == progression.POOL_CUSTOM:
            self.custom_chapters = progression.resolve_custom_chapters(
                self.goal_chapters, self.variant_picks, plando,
                opts.custom_mission_count.value, self.random
            )
        else:
            self.custom_chapters = ()

    def _draw_goal_chapters(self, opts: GotchaForceOptions) -> tuple[int, ...]:
        if opts.goal == opts.goal.option_custom:
            return (opts.goal_mission.value,)
        if opts.goal == opts.goal.option_random_mission:
            return (self.random.choice(progression.random_goal_candidates()),)
        pair = progression.FIXED_GOAL_CHAPTERS[opts.goal.value]
        if len(pair) > 1:
            return (self.random.choice(pair),)
        return pair

    @staticmethod
    def _plando_chapters(opts: GotchaForceOptions) -> tuple[int, ...]:
        if opts.mission_pool.value != progression.POOL_CUSTOM:
            return ()
        return tuple(sorted({int(entry) for entry in opts.custom_missions.value}))

    def _plan_gacha(self, opts: GotchaForceOptions) -> None:
        if opts.gacha_locations:
            self.gacha_chapters = gacha.gacha_chapters(
                self.enemy_assignments, self.chapters_in_pool,
                enemies.inserted_borgs(self.enemy_plan.inserts)
            )
        else:
            self.gacha_chapters = {}

    def _pick_starting_borg(self, opts: GotchaForceOptions, tracker_slot: TrackerSlot) -> list[int]:
        first_batch = self._chapters_open_at_start()
        if tracker_slot is not None:
            self.starting_borg = int(tracker_slot[slot_keys.STARTING_BORG])
            self.starting_borg_cost = int(tracker_slot[slot_keys.STARTING_BORG_COST])
        elif opts.starting_borg == opts.starting_borg.option_vanilla:
            self.starting_borg, self.starting_borg_cost = G_RED, G_RED_COST
        else:
            self.starting_borg = self.random.choice(self._starting_borg_candidates(opts, first_batch))
            self.starting_borg_cost = COSTS[self.starting_borg]
        in_logic = [c for c in first_batch
                    if self._in_logic_with_cap(c, self.starting_borg_cost)]
        if not in_logic:
            raise OptionError(
                f"Gotcha Force ({self.player_name}): no chapter of the "
                f"initial batch (among those Kou plays alone) is in logic with "
                f"the starting borg {self.starting_borg:#06x} (cost "
                f"{self.starting_borg_cost})"
            )
        return in_logic

    def _chapters_open_at_start(self) -> list[int]:
        return sorted(c for c, keys in self.keys_map.items()
                      if keys == 0 and progression.partner_requirement_met(c, ()))

    def _starting_borg_candidates(self, opts: GotchaForceOptions, first_batch: list[int]) -> list[int]:
        floor = STARTING_BORG_MIN_COST[opts.gf_logic_difficulty.value]
        candidates = [b for b in RANDOMIZABLE if COSTS[b] >= floor]
        if self.gf_ratio != UNLIMITED_RATIO:
            cost_to_open = self._cost_to_open_min_chapters(first_batch)
            candidates = [b for b in candidates
                          if COSTS[b] * self.gf_ratio >= cost_to_open]
        if not candidates:
            return [max(RANDOMIZABLE, key=lambda b: COSTS[b])]
        return sorted(candidates)

    def _cost_to_open_min_chapters(self, chapters: list[int]) -> int:
        costs = sorted(self.chapter_costs.get(c, 0) for c in chapters)
        if len(costs) >= MIN_START_CHAPTERS:
            return costs[MIN_START_CHAPTERS - 1]
        return costs[-1]

    def _in_logic_with_cap(self, chapter: int, cap: int) -> bool:
        return self.chapter_costs.get(chapter, 0) <= self.gf_ratio * cap

    def _pick_box_borgs(self, opts: GotchaForceOptions, tracker_slot: TrackerSlot) -> None:
        if tracker_slot is not None:
            self.box_unlocked = bool(tracker_slot.get(slot_keys.GOTCHA_BOX, 0))
            self.box_borgs = tuple(int(b) for b in tracker_slot.get(slot_keys.BOX_BORGS, ()))
        else:
            self.box_unlocked = opts.gotcha_box == opts.gotcha_box.option_unlocked
            self.box_borgs = tuple(sorted(self.random.sample(self._box_candidates(), INITIAL_BOX_BORG_COUNT)))

    def _box_candidates(self) -> list[int]:
        return sorted((set(BORGS) - NEVER_IN_POOL) - {self.starting_borg})

    def _plan_achievements(self, opts: GotchaForceOptions, tracker_slot: TrackerSlot) -> None:
        if tracker_slot is not None:
            inputs = self._achievement_inputs_from_slot(tracker_slot)
        else:
            inputs = self._achievement_inputs_from_options(opts)
        self.tribe_force_tribes = inputs.tribes
        if inputs.types:
            self.achievement_plan = achievements.plan_achievements(
                inputs.types,
                gacha_on=inputs.gacha_on,
                min_cost=inputs.min_cost,
                pool=self.chapters_in_pool,
                assignments=self.enemy_assignments,
                starting_borg=self.starting_borg,
                box_borgs=self.box_borgs,
                rng=inputs.rng,
                forced_borgs=inputs.forced_borgs,
                forced_ally_caps=inputs.forced_ally_chapters,
                tribes=inputs.tribes
            )
        else:
            self.achievement_plan = achievements.EMPTY_PLAN
        self.achievement_borg_items = items.borg_pool_item_names(
            self.achievement_plan.achievement_borgs, items.uses_fragments(opts)
        )

    @staticmethod
    def _achievement_inputs_from_slot(tracker_slot: dict) -> _AchievementInputs:
        types = tuple(sorted(tracker_slot.get(slot_keys.ACHIEVEMENT_TYPES, ())))
        return _AchievementInputs(
            types=types,
            gacha_on=bool(tracker_slot.get(slot_keys.GACHA_LOCATIONS, True)),
            min_cost=int(tracker_slot[slot_keys.TRIBE_FORCE_MIN_COST]) if types else 0,
            tribes=tuple(tracker_slot.get(slot_keys.TRIBE_FORCE_TRIBES, achievements.TRIBE_ORDER)),
            rng=None,
            forced_borgs=tuple(int(b) for b in tracker_slot.get(slot_keys.ACHIEVEMENT_BORGS, ())),
            forced_ally_chapters=tuple(int(c) for c in tracker_slot.get(slot_keys.ALLY_FINISHER_CHAPTERS, ()))
        )

    def _achievement_inputs_from_options(self, opts: GotchaForceOptions) -> _AchievementInputs:
        if not opts.achievements:
            return _AchievementInputs((), bool(opts.gacha_locations), opts.tribe_force_min_cost.value,
                                      (), self.random, (), ())
        return _AchievementInputs(
            types=tuple(sorted(opts.achievement_types.value)),
            gacha_on=bool(opts.gacha_locations),
            min_cost=opts.tribe_force_min_cost.value,
            tribes=achievements.canonical_tribes(opts.tribe_force_tribes.value),
            rng=self.random,
            forced_borgs=(),
            forced_ally_chapters=()
        )

    def _pick_start_areas(self, opts: GotchaForceOptions, tracker_slot: TrackerSlot,
                          in_logic: list[int]) -> None:
        if tracker_slot is not None:
            self.start_areas = set(tracker_slot.get(slot_keys.START_AREAS, ()))
        elif opts.area_access_items:
            self.start_areas = self._smallest_zone_cover(in_logic)
        else:
            self.start_areas = set()

    @staticmethod
    def _smallest_zone_cover(chapters: list[int]) -> set[int]:
        by_tile = Counter(CHAPTERS[c].tile for c in chapters)
        order = sorted(by_tile, key=lambda t: (t != STARTING_TILE, -by_tile[t], t))
        cover: set[int] = set()
        covered = 0
        target = min(MIN_START_CHAPTERS, len(chapters))
        for tile in order:
            cover.add(tile)
            covered += by_tile[tile]
            if covered >= target:
                break
        return cover

    def _push_starting_kit(self) -> None:
        for tile in sorted(self.start_areas):
            self.multiworld.push_precollected(
                self.create_item(items.area_access_item_name(tile))
            )
        if self.box_unlocked:
            self.multiworld.push_precollected(
                self.create_item(items.GOTCHA_BOX)
            )
        for _ in range(items.g_red_steps(self.starting_borg)):
            self.multiworld.push_precollected(self.create_item(items.PROG_G_RED))

    def _plan_progression_borgs(self, opts: GotchaForceOptions, tracker_slot: TrackerSlot) -> None:
        if tracker_slot is not None:
            self.progression_borgs = tuple(int(b) for b in tracker_slot.get(slot_keys.PROGRESSION_BORGS, ()))
        elif opts.gacha_locations:
            self.progression_borgs = self._draw_progression_borgs()
        else:
            self.progression_borgs = ()
        self.progression_borg_items = items.borg_pool_item_names(
            self.progression_borgs, items.uses_fragments(opts)
        )

    def _draw_progression_borgs(self) -> tuple[int, ...]:
        witnesses = set(self.achievement_plan.achievement_borgs)
        distributable = set(BORGS) - NEVER_IN_POOL - set(self.box_borgs)
        quota = len(distributable) // PROGRESSION_BORG_SHARE
        candidates = sorted(distributable - witnesses)
        missing = max(0, quota - len(witnesses))
        return tuple(sorted(witnesses | set(self.random.sample(candidates, missing))))

    def _plan_early_items(self, opts: GotchaForceOptions) -> None:
        fragments = items.uses_fragments(opts)
        early, plan = self._early_borgs_that_leave_room(
            self._promoted_by_piece_count(fragments), self._early_borg_count(opts), fragments
        )
        if plan is None:
            raise OptionError(
                f"Gotcha Force ({self.player_name}): the start is too "
                f"narrow: the missions open with the starting borg have "
                f"too few checks for the items that open the next one. "
                f"Choose starting_borg random_borg, raise mission_checks "
                f"or gf_logic_difficulty, or turn gacha_locations on"
            )
        self._add_local_early_items(early + plan.items)

    def _early_borgs_that_leave_room(self, candidates: list[int], count: int,
                                     fragments: bool) -> tuple[list[str], rules.OpeningPlan | None]:
        early: list[str] = []
        plan: rules.OpeningPlan | None = None
        for early_count in range(min(count, len(candidates)), -1, -1):
            early = [name for borg in candidates[:early_count]
                     for name in items.borg_pool_items(borg, fragments)]
            plan = rules.opening_items(self, len(early))
            if plan is not None and plan.fits:
                break
        return early, plan

    def _promoted_by_piece_count(self, fragments: bool) -> list[int]:
        return sorted(
            self.progression_borgs,
            key=lambda b: (len(items.borg_pool_items(b, fragments)), self.random.random())
        )

    @staticmethod
    def _early_borg_count(opts: GotchaForceOptions) -> int:
        if opts.mission_checks.value >= MORE_CHECKS_FROM:
            return EARLY_BORGS_WITH_MORE_CHECKS
        return EARLY_BORGS

    def _add_local_early_items(self, names: Iterable[str]) -> None:
        local_early = self.multiworld.local_early_items[self.player]
        for name in names:
            local_early[name] = local_early.get(name, 0) + 1

    @override
    def create_regions(self) -> None:
        regions.create_and_connect_regions(self)
        locations.create_all_locations(self)
        rules.create_goal_event(self)

    @override
    def create_items(self) -> None:
        items.create_all_items(self)

    @override
    def set_rules(self) -> None:
        rules.set_all_rules(self)

    @override
    def fill_hook(self, progitempool: list[Item], usefulitempool: list[Item],
                  filleritempool: list[Item],
                  fill_locations: list[Location]) -> None:
        opt = self.options.accessibility
        if opt != opt.option_minimal:
            return
        first = rules.goal_items(self)
        last = set(self.progression_borg_items) - set(self.achievement_borg_items)

        def turn(item: Item) -> int:
            if item.player != self.player:
                return PLACED_ANYWHERE
            if item.name in first:
                return PLACED_FIRST
            return PLACED_LAST if item.name in last else PLACED_ANYWHERE

        progitempool.sort(key=turn)

    @override
    def create_item(self, name: str) -> items.GotchaForceItem:
        return items.create_item(self, name)

    @override
    def get_filler_item_name(self) -> str:
        return items.FILLER_XP

    @staticmethod
    def interpret_slot_data(slot_data: Mapping[str, Any]) -> Mapping[str, Any]:
        return slot_data

    @override
    def fill_slot_data(self) -> Mapping[str, Any]:
        slot = self._option_slot_data()
        slot.update(self._plan_slot_data())
        slot.update(self._achievement_slot_data())
        return slot

    def _option_slot_data(self) -> dict[str, Any]:
        slot = dict(self.options.as_dict(*OPTIONS_IN_SLOT))
        slot[slot_keys.VERSION] = SLOT_DATA_VERSION
        slot[slot_keys.DEATH_CRYSTALS_IN_POOL] = self.crystals_in_pool
        return slot

    def _plan_slot_data(self) -> dict[str, Any]:
        return {
            slot_keys.PARTNER_LOGIC: True,
            slot_keys.GOAL_CHAPTERS: list(self.goal_chapters),
            slot_keys.VARIANT_PICKS: list(self.variant_picks),
            slot_keys.CUSTOM_CHAPTERS: list(self.custom_chapters),
            slot_keys.ENEMY_SEED: self.enemy_seed,
            slot_keys.STARTING_BORG: self.starting_borg,
            slot_keys.STARTING_BORG_COST: self.starting_borg_cost,
            slot_keys.START_AREAS: sorted(self.start_areas),
            slot_keys.PROGRESSION_BORGS: list(self.progression_borgs),
            slot_keys.BOX_BORGS: list(self.box_borgs),
        }

    def _achievement_slot_data(self) -> dict[str, Any]:
        opts = self.options
        plan = self.achievement_plan
        return {
            slot_keys.ACHIEVEMENTS: bool(opts.achievements),
            slot_keys.ACHIEVEMENT_TYPES: sorted(opts.achievement_types.value) if opts.achievements else [],
            slot_keys.TRIBE_FORCE_MIN_COST: opts.tribe_force_min_cost.value,
            slot_keys.TRIBE_FORCE_TRIBES: list(self.tribe_force_tribes),
            slot_keys.ACHIEVEMENT_BORGS: list(plan.achievement_borgs),
            slot_keys.ALLY_FINISHER_CHAPTERS: sorted(
                spec.chapter
                for spec in plan.specs
                if isinstance(spec, achievements.ChapterSpec) and spec.kind == achievements.TYPE_ALLY_FINISHER
            ),
        }
