from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .. import slot_keys
from ..data.achievements import STYLES, THEME_CHAPTERS, TRIBES
from ..data.borgs import BORGS
from ..data.chapters import CHAPTERS
from ..data.spawns import SIGNATURE_BORGS
from ..locations import LOCATION_NAME_TO_ID, achievement_location_name
from ..logic import achievements
from ..logic.achievements import (
    ChapterSpec,
    CommanderChapterSpec,
    CommanderSpec,
    Spec,
    TribeSpec,
)
from ..logic.progression import PARTNER_CHOICE, PARTNER_FIXED
from .logic import (
    ApState,
    SlotData,
    chapter_pool_for_slot,
    gf_cap_value,
    slot_value,
    unlocked_partners,
)


@dataclass(frozen=True)
class _LogicView:
    state: ApState
    slot: SlotData
    in_logic: set[int]
    assignments: Mapping[int, int | None]
    gacha_on: bool
    starting_borg: int
    box_borgs: tuple[int, ...]
    progression_borgs: tuple[int, ...]
    min_cost: int
    starting_cost: int
    recruited: set[int]
    owned_tribes: set[str | None]

    @classmethod
    def of(
        cls, state: ApState, slot: SlotData, in_logic: set[int], assignments: Mapping[int, int | None]
    ) -> _LogicView:
        starting_borg = int(slot_value(slot, slot_keys.STARTING_BORG))
        box_borgs = tuple(slot_value(slot, slot_keys.BOX_BORGS))
        return cls(
            state,
            slot,
            in_logic,
            assignments,
            gacha_on=bool(slot_value(slot, slot_keys.GACHA_LOCATIONS)),
            starting_borg=starting_borg,
            box_borgs=box_borgs,
            progression_borgs=tuple(slot_value(slot, slot_keys.PROGRESSION_BORGS)),
            min_cost=int(slot_value(slot, slot_keys.TRIBE_FORCE_MIN_COST)),
            starting_cost=int(slot_value(slot, slot_keys.STARTING_BORG_COST)),
            recruited=unlocked_partners(state),
            owned_tribes={TRIBES.get(starting_borg)} | {TRIBES.get(b) for b in box_borgs},
        )

    def from_start_or_box(self, borg_id: int) -> bool:
        return borg_id == self.starting_borg or borg_id in self.box_borgs

    def style_ok(self, tribes: Iterable[str]) -> bool:
        wanted = set(tribes)
        if wanted & self.owned_tribes:
            return True
        if self.gacha_on:
            return any(self.borg_complete(b) for b in self.progression_borgs if TRIBES.get(b) in wanted)
        return any(
            c in self.in_logic for c in achievements.farm_chapters(tuple(wanted), self.in_logic, self.assignments)
        )

    def borg_complete(self, borg_id: int) -> bool:
        if borg_id in self.state.borgs:
            return True
        return self.state.fragments.get(borg_id, 0) >= BORGS[borg_id].fragments


def achievement_plan_for_slot(
    slot: SlotData,
    assignments: Mapping[int, int | None],
) -> achievements.AchievementPlan:
    if not slot_value(slot, slot_keys.ACHIEVEMENTS):
        return achievements.EMPTY_PLAN
    return achievements.plan_achievements(
        tuple(slot_value(slot, slot_keys.ACHIEVEMENT_TYPES)),
        gacha_on=bool(slot_value(slot, slot_keys.GACHA_LOCATIONS)),
        min_cost=int(slot_value(slot, slot_keys.TRIBE_FORCE_MIN_COST)),
        pool=chapter_pool_for_slot(slot),
        assignments=assignments,
        starting_borg=int(slot_value(slot, slot_keys.STARTING_BORG)),
        box_borgs=tuple(slot_value(slot, slot_keys.BOX_BORGS)),
        rng=None,
        forced_borgs=tuple(slot_value(slot, slot_keys.ACHIEVEMENT_BORGS)),
        forced_ally_caps=tuple(slot_value(slot, slot_keys.ALLY_FINISHER_CHAPTERS)),
        tribes=tuple(slot_value(slot, slot_keys.TRIBE_FORCE_TRIBES)),
    )


def achievements_by_chapter_map(
    specs: Iterable[Spec],
) -> dict[int, set[int]]:
    out: dict[int, set[int]] = {}
    for raw_spec in specs:
        spec = achievements.as_spec(raw_spec)
        if not isinstance(spec, (ChapterSpec, CommanderChapterSpec)):
            continue
        if spec.kind in achievements.ANCHORED_TYPES:
            out.setdefault(spec.chapter, set()).add(achievement_id(spec))
    return out


def achievement_id(spec: Spec) -> int:
    return LOCATION_NAME_TO_ID[achievement_location_name(spec)]


def achievements_in_logic(
    specs: Iterable[Spec], state: ApState, slot: SlotData, in_logic: set[int], assignments: Mapping[int, int | None]
) -> set[int]:
    specs = [achievements.as_spec(spec) for spec in specs]
    if not specs:
        return set()
    view = _LogicView.of(state, slot, in_logic, assignments)
    return {achievement_id(spec) for spec in specs if _spec_in_logic(view, spec)}


def _spec_in_logic(view: _LogicView, spec: Spec) -> bool:
    if spec.kind not in _IN_LOGIC:
        return False
    if spec.kind not in achievements.BOX_FREE_TYPES and not view.state.gotcha_box:
        return False
    return _IN_LOGIC[spec.kind](view, spec)


def _anchored_in_logic(view: _LogicView, spec: ChapterSpec) -> bool:
    return spec.chapter in view.in_logic


def _partner_style_in_logic(view: _LogicView, spec: CommanderSpec) -> bool:
    deployable = achievements.deployable_chapters(spec.commander, view.in_logic)
    fixed = [c for c in deployable if CHAPTERS[c].partner_mode in PARTNER_FIXED]
    eligible = [c for c in deployable if CHAPTERS[c].partner_mode == PARTNER_CHOICE]
    can_deploy = bool(fixed) or (spec.commander in view.recruited and bool(eligible))
    return can_deploy and view.style_ok(STYLES[spec.commander])


def _commander_style_in_logic(view: _LogicView, spec: CommanderSpec) -> bool:
    return bool(achievements.rival_chapters(spec.commander, view.in_logic)) and view.style_ok(STYLES[spec.commander])


def _commander_style_all_in_logic(view: _LogicView, spec: CommanderChapterSpec) -> bool:
    return spec.chapter in view.in_logic and view.style_ok(STYLES[spec.commander])


def _theme_in_logic(view: _LogicView, spec: ChapterSpec) -> bool:
    return spec.chapter in view.in_logic and view.style_ok((THEME_CHAPTERS[spec.chapter],))


def _ace_duel_in_logic(view: _LogicView, spec: CommanderSpec) -> bool:
    ace = SIGNATURE_BORGS[spec.commander]
    if view.from_start_or_box(ace):
        ace_owned = True
    elif view.gacha_on:
        ace_owned = view.borg_complete(ace)
    else:
        ace_owned = any(
            c in view.in_logic
            for c in achievements.chapters_with_id(ace, chapter_pool_for_slot(view.slot), view.assignments)
        )
    return bool(achievements.rival_chapters(spec.commander, view.in_logic)) and ace_owned


def _tribe_force_in_logic(view: _LogicView, spec: TribeSpec) -> bool:
    if gf_cap_value(view.state, view.starting_cost) < view.min_cost:
        return False
    if view.gacha_on:
        witnesses = achievements.tribe_force_witnesses(
            spec.tribe,
            view.starting_borg,
            view.box_borgs,
            tuple(slot_value(view.slot, slot_keys.ACHIEVEMENT_BORGS)),
            view.min_cost,
        )
        return all(view.borg_complete(b) for b in witnesses)
    witness_chapters = achievements.tribe_force_witness_chapters(
        spec.tribe,
        chapter_pool_for_slot(view.slot),
        view.assignments,
        view.starting_borg,
        view.box_borgs,
        view.min_cost,
    )
    covered = (
        bool(witness_chapters)
        or TRIBES.get(view.starting_borg) == spec.tribe
        or any(TRIBES.get(b) == spec.tribe for b in view.box_borgs)
    )
    return covered and all(c in view.in_logic for c in witness_chapters)


_IN_LOGIC: dict[str, Callable[[_LogicView, Any], bool]] = {
    achievements.TYPE_ALLY_FINISHER: _anchored_in_logic,
    achievements.TYPE_NO_CASUALTIES: _anchored_in_logic,
    achievements.TYPE_PARTNER_STYLE: _partner_style_in_logic,
    achievements.TYPE_COMMANDER_STYLE: _commander_style_in_logic,
    achievements.TYPE_COMMANDER_STYLE_ALL: _commander_style_all_in_logic,
    achievements.TYPE_THEME: _theme_in_logic,
    achievements.TYPE_ACE_DUEL: _ace_duel_in_logic,
    achievements.TYPE_TRIBE_FORCE: _tribe_force_in_logic,
}
