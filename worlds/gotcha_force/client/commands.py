from __future__ import annotations

from typing import TYPE_CHECKING, Final

from CommonClient import ClientCommandProcessor, logger

from .. import slot_keys
from ..data.chapters import CHAPTERS
from ..logic import progression
from . import achievements, logic, tracker

if TYPE_CHECKING:
    from . import GotchaForceContext
    from .logic import ApState, SlotData

SCOPE_ALL: Final = "all"

CHECKS_OUT_OF_LOGIC_MARK: Final = " !"


class GotchaForceCommandProcessor(ClientCommandProcessor):
    ctx: GotchaForceContext

    def _cmd_checks(self, scope: str = "") -> None:
        ctx = self.ctx
        view = tracker.in_logic_view(ctx)
        if view is None:
            logger.info("No data from the server or the game yet.")
            return
        show_all = scope.strip().lower() == SCOPE_ALL
        slot, ap_state, allowed, in_logic = view
        out_of_logic = len(allowed) - len(in_logic)
        pending = logic.pending_checks_by_chapter(
            allowed if show_all else in_logic,
            set(ctx.missing_locations),
            logic.slot_value(slot, slot_keys.MISSION_CHECKS),
            ctx.gacha_by_chapter,
            ctx.ach_by_chapter,
            self._obtainable_achievements(show_all, ap_state, slot, in_logic),
        )
        if not pending:
            logger.info(_no_pending_message(show_all, out_of_logic))
            return
        logger.info(_pending_header(show_all, pending, out_of_logic))
        by_zone = _lines_by_zone(pending, in_logic)
        for zone in sorted(by_zone):
            logger.info(f"  {zone}:")
            for line in by_zone[zone]:
                logger.info(f"    {line}")

    def _obtainable_achievements(
        self, show_all: bool, ap_state: ApState, slot: SlotData, in_logic: set[int]
    ) -> set[int] | None:
        ctx = self.ctx
        if show_all or not ctx.achievement_specs:
            return None
        return achievements.achievements_in_logic(
            ctx.achievement_specs, ap_state, slot, in_logic, ctx.achievement_assignments
        )

    def _cmd_mission(self) -> None:
        chapter = self.ctx.last_chapter
        if chapter is None:
            logger.info("No chapter selected yet.")
            return
        partner_text = f"; {progression.partner_label(chapter)}" if chapter in CHAPTERS else ""
        logger.info(
            f"Current chapter: {tracker.chapter_label(chapter)} "
            f"(zone: {logic.chapter_zone_name(chapter)}{partner_text})"
        )

    def _cmd_dolphin(self) -> None:
        ctx = self.ctx
        state = "connected" if ctx.dolphin.is_connected() else "disconnected"
        logger.info(f"Dolphin: {state}; valid game: {ctx.game_valid}")


def _no_pending_message(show_all: bool, out_of_logic: int) -> str:
    if show_all:
        return "No checks left in the missions you can play."
    if out_of_logic:
        return f"No checks left in the missions in logic ({out_of_logic} playable missions are out of logic)."
    return "No checks left in the missions in logic."


def _pending_header(show_all: bool, pending: dict[int, int], out_of_logic: int) -> str:
    total = sum(pending.values())
    if show_all:
        return (
            f"Pending checks in ALL playable missions "
            f"({total} in {len(pending)} missions; including "
            f"{out_of_logic} out of logic due to GF Energy):"
        )
    if out_of_logic:
        return (
            f"Pending checks IN LOGIC ({total} in {len(pending)} missions; "
            f"{out_of_logic} playable missions are out of logic "
            f"due to GF Energy - see /checks all):"
        )
    return f"Pending checks IN LOGIC ({total} in {len(pending)} missions):"


def _lines_by_zone(pending: dict[int, int], in_logic: set[int]) -> dict[str, list[str]]:
    by_zone: dict[str, list[str]] = {}
    for chapter, count in sorted(pending.items()):
        mark = "" if chapter in in_logic else CHECKS_OUT_OF_LOGIC_MARK
        by_zone.setdefault(logic.chapter_zone_name(chapter), []).append(
            f"{tracker.chapter_label(chapter)} ({count}){mark}"
        )
    return by_zone
