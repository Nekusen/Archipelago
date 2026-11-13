from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from Options import OptionError

from ..data.achievements import NO_CASUALTIES_CHAPTERS, STYLES, THEME_CHAPTERS, TRIBES
from ..data.addresses import PARTNER_BATTLE_SLOT
from ..data.borgs import BORGS, NEVER_IN_POOL
from ..data.chapters import CHAPTERS
from ..data.gacha import GACHA_REGISTERS
from ..data.spawns import BOSS_ADDRS, SIGNATURE_BORGS, SPAWNS
from .progression import PARTNER_CHOICE, PARTNER_FIXED

TYPE_PARTNER_STYLE = "partner_style"
TYPE_COMMANDER_STYLE = "commander_style"
TYPE_COMMANDER_STYLE_ALL = "commander_style_all"
TYPE_TRIBE_FORCE = "tribe_force"
TYPE_THEME = "theme_missions"
TYPE_ALLY_FINISHER = "ally_finisher"
TYPE_NO_CASUALTIES = "no_casualties"
TYPE_ACE_DUEL = "ace_duel"

SPEC_ORDER = (
    TYPE_PARTNER_STYLE,
    TYPE_COMMANDER_STYLE,
    TYPE_COMMANDER_STYLE_ALL,
    TYPE_THEME,
    TYPE_ACE_DUEL,
    TYPE_ALLY_FINISHER,
    TYPE_NO_CASUALTIES,
    TYPE_TRIBE_FORCE,
)

ALL_TYPES = frozenset(SPEC_ORDER)

STYLE_TYPES = frozenset({TYPE_PARTNER_STYLE, TYPE_COMMANDER_STYLE, TYPE_COMMANDER_STYLE_ALL})

BOX_FREE_TYPES = frozenset({TYPE_ALLY_FINISHER, TYPE_NO_CASUALTIES})

ANCHORED_TYPES = frozenset({TYPE_THEME, TYPE_ALLY_FINISHER, TYPE_NO_CASUALTIES,
                            TYPE_COMMANDER_STYLE_ALL})

ALLY_FINISHER_SHARE = 0.10
MIN_ALLY_FINISHER_CHECKS = 1

BOSS_CHAPTERS = frozenset(
    c for c, rows in SPAWNS.items()
    if any(spawn.cell in BOSS_ADDRS for spawn in rows)
)

TRIBE_ORDER = ("Air", "Angel", "Bug", "Death", "Demon", "Dragon",
               "Fortress", "Girl", "Gun", "Hero", "Idol", "Knight",
               "Knuckle", "Machine", "Musha", "Ninja", "Nurse",
               "Tank", "Wing", "Wizard")

FARMABLE = frozenset(borg_id for borg_id, register in GACHA_REGISTERS.items()
                     if register.thresholds[0] >= 0)

DISTRIBUTABLE = frozenset(set(BORGS) - NEVER_IN_POOL)

NO_LOSSES = 0


class CommanderSpec(NamedTuple):
    kind: str
    commander: int


class ChapterSpec(NamedTuple):
    kind: str
    chapter: int


class CommanderChapterSpec(NamedTuple):
    kind: str
    commander: int
    chapter: int


class TribeSpec(NamedTuple):
    kind: str
    tribe: str


Spec = CommanderSpec | ChapterSpec | CommanderChapterSpec | TribeSpec


class AchievementPlan(NamedTuple):
    specs: tuple[Spec, ...]
    tribe_force_tribes: tuple[str, ...]
    achievement_borgs: tuple[int, ...]


EMPTY_PLAN = AchievementPlan((), (), ())


@dataclass
class _Plan:
    gacha_on: bool
    min_cost: int
    chapters: list[int]
    assignments: Mapping[int, int | None]
    starting_borg: int
    box_borgs: Sequence[int]
    rng: random.Random | None
    forced_borgs: Sequence[int]
    forced_ally_chapters: Sequence[int]
    tribes: Iterable[str] | None
    chapter_set: set[int] = field(init=False)
    owned_tribes: set[str | None] = field(init=False)
    guaranteed: dict[int, frozenset[int]] = field(init=False)
    farm_tribes: set[str] = field(init=False)

    def __post_init__(self) -> None:
        self.chapter_set = set(self.chapters)
        self.owned_tribes = {TRIBES.get(self.starting_borg)} | {TRIBES.get(b) for b in self.box_borgs}
        self.guaranteed = ({} if self.gacha_on
                           else {c: guaranteed_farmable_borgs(c, self.assignments) for c in self.chapters})
        self.farm_tribes = {TRIBES[i] for ids in self.guaranteed.values() for i in ids}

    def ownable(self, tribes: Sequence[str]) -> bool:
        if set(tribes) & self.owned_tribes:
            return True
        if self.gacha_on:
            return any(TRIBES.get(b) in set(tribes) for b in DISTRIBUTABLE)
        return bool(set(tribes) & self.farm_tribes)

    def deliverable_borgs(self, tribe: str | None = None) -> list[int]:
        return sorted(b for b in DISTRIBUTABLE
                      if (tribe is None or TRIBES.get(b) == tribe)
                      and not self.from_start_or_box(b))

    def from_start_or_box(self, borg_id: int) -> bool:
        return borg_id == self.starting_borg or borg_id in self.box_borgs


class BattleOutcome(NamedTuple):
    chapter: int
    partner: int
    force_ids: Sequence[int]
    force_tribes: set[str]
    force_cost: int
    min_cost: int
    finisher_slot: int | None
    own_losses: int | None


def canonical_tribes(values: Iterable[str]) -> tuple[str, ...]:
    wanted = {str(v).casefold() for v in values}
    return tuple(t for t in TRIBE_ORDER if t.casefold() in wanted)


def farm_chapters(tribes: Sequence[str], chapters: Iterable[int],
                  assignments: Mapping[int, int | None]) -> list[int]:
    wanted = set(tribes)
    return sorted(c for c in chapters
                  if any(TRIBES[i] in wanted
                         for i in guaranteed_farmable_borgs(c, assignments)))


def guaranteed_farmable_borgs(chapter: int, assignments: Mapping[int, int | None]) -> frozenset[int]:
    out: set[int] = set()
    for spawn in SPAWNS.get(chapter, ()):
        borg_id = assignments.get(spawn.cell, spawn.borg)
        if borg_id is not None:
            if borg_id in FARMABLE:
                out.add(borg_id)
        elif spawn.choices:
            tribes = {TRIBES.get(o) for o in spawn.choices}
            if (len(tribes) == 1 and None not in tribes
                    and all(o in FARMABLE for o in spawn.choices)):
                out.update(spawn.choices)
    return frozenset(out)


def tribe_force_witnesses(tribe: str, starting_borg: int,
                          box_borgs: Sequence[int],
                          achievement_borgs: Sequence[int],
                          min_cost: int) -> tuple[int, ...]:
    base = owned_tribe_cost(tribe, starting_borg, box_borgs)
    witnesses: list[int] = []
    candidates = sorted((b for b in achievement_borgs
                         if TRIBES.get(b) == tribe),
                        key=lambda b: (-BORGS[b].cost, b))
    for borg in candidates:
        if base >= min_cost:
            break
        base += BORGS[borg].cost
        witnesses.append(borg)
    return tuple(witnesses)


def owned_tribe_cost(tribe: str, starting_borg: int, box_borgs: Sequence[int]) -> int:
    total = 0
    if TRIBES.get(starting_borg) == tribe and starting_borg in BORGS:
        total += BORGS[starting_borg].cost
    for borg in box_borgs:
        if TRIBES.get(borg) == tribe:
            total += BORGS[borg].cost
    return total


def tribe_force_witness_chapters(tribe: str, chapters: Iterable[int],
                                 assignments: Mapping[int, int | None],
                                 starting_borg: int,
                                 box_borgs: Sequence[int],
                                 min_cost: int) -> tuple[int, ...]:
    total = owned_tribe_cost(tribe, starting_borg, box_borgs)
    seen: set[int] = set()
    witnesses: list[int] = []
    for chapter in _chapters_by_sphere(chapters):
        if total >= min_cost:
            break
        new_ids = {i for i in guaranteed_farmable_borgs(chapter, assignments)
                   if TRIBES[i] == tribe and i not in seen}
        if not new_ids:
            continue
        seen |= new_ids
        total += sum(BORGS[i].cost for i in new_ids)
        witnesses.append(chapter)
    return tuple(witnesses) if total >= min_cost else ()


def _chapters_by_sphere(chapters: Iterable[int]) -> list[int]:
    return sorted(chapters, key=lambda c: (CHAPTERS[c].sphere, c))


def plan_achievements(types: Iterable[str], gacha_on: bool, min_cost: int,
                      pool: Sequence[int],
                      assignments: Mapping[int, int | None],
                      starting_borg: int, box_borgs: Sequence[int],
                      rng: random.Random | None = None,
                      forced_borgs: Sequence[int] = (),
                      forced_ally_caps: Sequence[int] = (),
                      tribes: Iterable[str] | None = None) -> AchievementPlan:
    active = frozenset(types) & ALL_TYPES
    if not active:
        return EMPTY_PLAN
    plan = _Plan(gacha_on, min_cost, list(pool), assignments, starting_borg, box_borgs,
                 rng, forced_borgs, forced_ally_caps, tribes)
    specs: list[Spec] = []
    for kind in SPEC_ORDER:
        if kind in active:
            specs += _SPECS_OF[kind](plan)
    viable_tribes = [spec.tribe for spec in specs if isinstance(spec, TribeSpec)]
    witnesses = set(forced_borgs)
    if gacha_on and rng is not None and not forced_borgs:
        witnesses = _draw_witnesses(plan, rng, specs, viable_tribes)
    return AchievementPlan(tuple(specs), tuple(viable_tribes), tuple(sorted(witnesses)))


def _partner_style_specs(plan: _Plan) -> list[Spec]:
    return [CommanderSpec(TYPE_PARTNER_STYLE, k) for k in sorted(STYLES)
            if deployable_chapters(k, plan.chapters) and plan.ownable(STYLES[k])]


def deployable_chapters(commander: int, chapters: Iterable[int]) -> list[int]:
    return sorted(c for c in chapters if _deployable(c, commander))


def _deployable(chapter: int, commander: int) -> bool:
    header = CHAPTERS[chapter]
    if header.partner_mode in PARTNER_FIXED:
        return header.partner == commander
    return header.partner_mode == PARTNER_CHOICE and commander not in header.antagonists


def _commander_style_specs(plan: _Plan) -> list[Spec]:
    return [CommanderSpec(TYPE_COMMANDER_STYLE, k) for k in sorted(STYLES)
            if rival_chapters(k, plan.chapters) and plan.ownable(STYLES[k])]


def rival_chapters(commander: int, chapters: Iterable[int]) -> list[int]:
    return sorted(c for c in chapters if commander in CHAPTERS[c].antagonists)


def _commander_style_all_specs(plan: _Plan) -> list[Spec]:
    return [CommanderChapterSpec(TYPE_COMMANDER_STYLE_ALL, k, c)
            for c in sorted(plan.chapter_set)
            for k in CHAPTERS[c].antagonists
            if plan.ownable(STYLES[k])]


def _theme_specs(plan: _Plan) -> list[Spec]:
    return [ChapterSpec(TYPE_THEME, c) for c in sorted(THEME_CHAPTERS)
            if c in plan.chapter_set and plan.ownable((THEME_CHAPTERS[c],))]


def _ace_duel_specs(plan: _Plan) -> list[Spec]:
    return [CommanderSpec(TYPE_ACE_DUEL, k) for k in sorted(SIGNATURE_BORGS)
            if rival_chapters(k, plan.chapters) and _ace_reachable(plan, SIGNATURE_BORGS[k])]


def _ace_reachable(plan: _Plan, ace: int) -> bool:
    if plan.from_start_or_box(ace):
        return True
    if plan.gacha_on:
        return ace in DISTRIBUTABLE
    return bool(chapters_with_id(ace, plan.chapters, plan.assignments))


def chapters_with_id(borg_id: int, chapters: Iterable[int],
                     assignments: Mapping[int, int | None]) -> list[int]:
    return sorted(c for c in chapters
                  if borg_id in guaranteed_farmable_borgs(c, assignments))


def _ally_finisher_specs(plan: _Plan) -> list[Spec]:
    eligible = sorted(c for c in plan.chapter_set
                      if CHAPTERS[c].partner_mode == PARTNER_CHOICE
                      and c not in BOSS_CHAPTERS)
    if plan.forced_ally_chapters:
        sample = sorted(set(plan.forced_ally_chapters) & set(eligible))
    elif plan.rng is not None and eligible:
        n = max(MIN_ALLY_FINISHER_CHECKS, round(ALLY_FINISHER_SHARE * len(eligible)))
        sample = sorted(plan.rng.sample(eligible, min(n, len(eligible))))
    else:
        sample = []
    return [ChapterSpec(TYPE_ALLY_FINISHER, c) for c in sample]


def _no_casualties_specs(plan: _Plan) -> list[Spec]:
    return [ChapterSpec(TYPE_NO_CASUALTIES, c) for c in NO_CASUALTIES_CHAPTERS
            if c in plan.chapter_set and _has_vanilla_enemies(c, plan.assignments)]


def _has_vanilla_enemies(chapter: int, assignments: Mapping[int, int | None]) -> bool:
    return all(spawn.cell not in assignments
               for spawn in SPAWNS.get(chapter, ()))


def _tribe_force_specs(plan: _Plan) -> list[Spec]:
    return [TribeSpec(TYPE_TRIBE_FORCE, t) for t in _viable_tribes(plan)]


def _viable_tribes(plan: _Plan) -> list[str]:
    allowed = set(TRIBE_ORDER) if plan.tribes is None else set(plan.tribes)
    return [t for t in TRIBE_ORDER
            if t in allowed and _tribe_reachable_cost(plan, t) >= plan.min_cost]


def _tribe_reachable_cost(plan: _Plan, tribe: str) -> int:
    total = owned_tribe_cost(tribe, plan.starting_borg, plan.box_borgs)
    if plan.gacha_on:
        return total + sum(BORGS[b].cost for b in plan.deliverable_borgs(tribe))
    tribe_ids = {i for ids in plan.guaranteed.values() for i in ids if TRIBES[i] == tribe}
    return total + sum(BORGS[i].cost for i in tribe_ids if not plan.from_start_or_box(i))


_SPECS_OF: dict[str, Callable[[_Plan], list[Spec]]] = {
    TYPE_PARTNER_STYLE: _partner_style_specs,
    TYPE_COMMANDER_STYLE: _commander_style_specs,
    TYPE_COMMANDER_STYLE_ALL: _commander_style_all_specs,
    TYPE_THEME: _theme_specs,
    TYPE_ACE_DUEL: _ace_duel_specs,
    TYPE_ALLY_FINISHER: _ally_finisher_specs,
    TYPE_NO_CASUALTIES: _no_casualties_specs,
    TYPE_TRIBE_FORCE: _tribe_force_specs,
}


def _draw_witnesses(plan: _Plan, rng: random.Random,
                    specs: Sequence[Spec], tribes: Sequence[str]) -> set[int]:
    chosen: set[int] = set()

    def cover(wanted_tribes: Sequence[str]) -> None:
        wanted = set(wanted_tribes)
        if wanted & plan.owned_tribes:
            return
        if any(TRIBES.get(b) in wanted for b in chosen):
            return
        matching = [b for b in plan.deliverable_borgs() if TRIBES.get(b) in wanted]
        if not matching:
            raise OptionError(
                f"achievements: no distributable candidate for {wanted_tribes}"
            )
        chosen.add(rng.choice(matching))

    for spec in specs:
        if isinstance(spec, (CommanderSpec, CommanderChapterSpec)) and spec.kind in STYLE_TYPES:
            cover(STYLES[spec.commander])
        elif isinstance(spec, ChapterSpec) and spec.kind == TYPE_THEME:
            cover((THEME_CHAPTERS[spec.chapter],))
        elif isinstance(spec, CommanderSpec) and spec.kind == TYPE_ACE_DUEL:
            ace = SIGNATURE_BORGS[spec.commander]
            if not plan.from_start_or_box(ace):
                chosen.add(ace)
    for tribe in tribes:
        base = owned_tribe_cost(tribe, plan.starting_borg, plan.box_borgs)
        base += sum(BORGS[b].cost for b in chosen if TRIBES.get(b) == tribe)
        while base < plan.min_cost:
            candidates = [b for b in plan.deliverable_borgs(tribe) if b not in chosen]
            if not candidates:
                raise OptionError(
                    f"achievements: tribe {tribe} does not cover {plan.min_cost}"
                )
            borg = rng.choice(candidates)
            chosen.add(borg)
            base += BORGS[borg].cost
    return chosen


def achievements_met(specs: Iterable[Spec], chapter: int, partner: int,
                     force_ids: Sequence[int], force_cost: int,
                     min_cost: int,
                     finisher_slot: int | None = None,
                     own_losses: int | None = None) -> list[Spec]:
    outcome = BattleOutcome(chapter, partner, force_ids,
                            {TRIBES[i] for i in force_ids if i in TRIBES},
                            force_cost, min_cost, finisher_slot, own_losses)
    return [spec for spec in specs
            if spec[0] in _MET and _MET[spec[0]](outcome, as_spec(spec))]


def _met_partner_style(outcome: BattleOutcome, spec: CommanderSpec) -> bool:
    return (outcome.partner == spec.commander
            and bool(outcome.force_tribes & set(STYLES[spec.commander])))


def _met_commander_style(outcome: BattleOutcome, spec: CommanderSpec) -> bool:
    return (spec.commander in CHAPTERS[outcome.chapter].antagonists
            and bool(outcome.force_tribes & set(STYLES[spec.commander])))


def _met_commander_style_all(outcome: BattleOutcome, spec: CommanderChapterSpec) -> bool:
    return (outcome.chapter == spec.chapter
            and bool(outcome.force_tribes & set(STYLES[spec.commander])))


def _met_theme(outcome: BattleOutcome, spec: ChapterSpec) -> bool:
    return outcome.chapter == spec.chapter and THEME_CHAPTERS[spec.chapter] in outcome.force_tribes


def _met_tribe_force(outcome: BattleOutcome, spec: TribeSpec) -> bool:
    return (bool(outcome.force_ids) and outcome.force_tribes == {spec.tribe}
            and outcome.force_cost >= outcome.min_cost)


def _met_ally_finisher(outcome: BattleOutcome, spec: ChapterSpec) -> bool:
    return outcome.chapter == spec.chapter and outcome.finisher_slot == PARTNER_BATTLE_SLOT


def _met_no_casualties(outcome: BattleOutcome, spec: ChapterSpec) -> bool:
    return outcome.chapter == spec.chapter and outcome.own_losses == NO_LOSSES


def _met_ace_duel(outcome: BattleOutcome, spec: CommanderSpec) -> bool:
    return (spec.commander in CHAPTERS[outcome.chapter].antagonists
            and SIGNATURE_BORGS[spec.commander] in outcome.force_ids)


_MET: dict[str, Callable[[BattleOutcome, Any], bool]] = {
    TYPE_PARTNER_STYLE: _met_partner_style,
    TYPE_COMMANDER_STYLE: _met_commander_style,
    TYPE_COMMANDER_STYLE_ALL: _met_commander_style_all,
    TYPE_THEME: _met_theme,
    TYPE_TRIBE_FORCE: _met_tribe_force,
    TYPE_ALLY_FINISHER: _met_ally_finisher,
    TYPE_NO_CASUALTIES: _met_no_casualties,
    TYPE_ACE_DUEL: _met_ace_duel,
}


def as_spec(spec: Spec | tuple) -> Spec:
    if isinstance(spec, (CommanderSpec, ChapterSpec, CommanderChapterSpec, TribeSpec)):
        return spec
    kind = spec[0]
    if kind == TYPE_COMMANDER_STYLE_ALL:
        return CommanderChapterSpec(*spec)
    if kind == TYPE_TRIBE_FORCE:
        return TribeSpec(*spec)
    if kind in ANCHORED_TYPES:
        return ChapterSpec(*spec)
    return CommanderSpec(*spec)
