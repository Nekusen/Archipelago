from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import Utils
from CommonClient import (
    CommonContext,
    get_base_parser,
    gui_enabled,
    handle_url_arg,
    logger,
    server_loop,
)
from NetUtils import ClientStatus

from .. import slot_keys
from ..data import addresses
from ..game import CLIENT_NAME, GAME_NAME
from ..logic import enemies
from ..logic.enemies import EnemyPlan
from . import achievements as client_achievements
from . import gui, inventory, queues, tracker
from . import logic as client_logic
from .commands import GotchaForceCommandProcessor
from .dolphin import DolphinAdapter
from .guardian import Guardian
from .queues import QueueEdit

if TYPE_CHECKING:
    from kvui import GameManager

__all__ = ["DolphinAdapter", "GotchaForceCommandProcessor",
           "GotchaForceContext", "Guardian", "game_watcher", "launch"]

TICK = 0.25

FAILURE_SUMMARY_SECONDS = 60
FAILURE_SUMMARY_TICKS = int(FAILURE_SUMMARY_SECONDS / TICK)

HOOK_RETRY = 2.0

RECEIVE_ALL_ITEMS = 0b111


def launch(*launch_args: str) -> None:
    async def main() -> None:
        parser = get_base_parser()
        parser.add_argument("--name", default=None,
                            help="Slot name to connect as.")
        parser.add_argument("url", nargs="?",
                            help="Archipelago connection url")
        args = parser.parse_args(launch_args)
        args = handle_url_arg(args, parser=parser)
        try:
            ctx = GotchaForceContext(args.connect, args.password)
        except ImportError as exc:
            logger.error(str(exc))
            Utils.messagebox("Gotcha Force Client", str(exc), error=True)
            return
        if args.name:
            ctx.auth = args.name
        ctx.server_task = asyncio.create_task(server_loop(ctx),
                                              name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        watcher = asyncio.create_task(game_watcher(ctx), name="GameWatcher")
        await ctx.exit_event.wait()
        watcher.cancel()
        await ctx.shutdown()

    Utils.init_logging(CLIENT_NAME, exception_logger="Client")
    import colorama
    colorama.just_fix_windows_console()
    asyncio.run(main())
    colorama.deinit()


class GotchaForceContext(CommonContext):
    game = GAME_NAME
    items_handling = RECEIVE_ALL_ITEMS
    command_processor = GotchaForceCommandProcessor

    def __init__(self, server_address: str | None,
                 password: str | None) -> None:
        super().__init__(server_address, password)
        self.dolphin = DolphinAdapter()
        self.slot_data: dict[str, Any] | None = None
        self.game_valid = False
        self.gacha_by_chapter: dict[int, set[int]] = {}
        self.achievement_specs: tuple = ()
        self.ach_by_chapter: dict[int, set[int]] = {}
        self.achievement_assignments: dict[int, int | None] = {}
        self.chapter_costs: dict[int, int] = {}
        self.last_allowed: set[int] | None = None
        self.enemy_writes: dict[int, int | None] = {}
        self.enemy_byte_writes: dict[int, int] = {}
        self.queue_edits: dict[int, QueueEdit] = {}
        self.queue_arena: dict[int, int] = {}
        self.gacha_map: dict[int, list[int]] = {}
        self.last_chapter: int | None = None
        self.goal_sent = False
        self._warned_invalid = False

    def go_mode(self) -> bool | None:
        view = tracker.in_logic_view(self)
        if view is None:
            return None
        slot, _ap, _allowed, in_logic = view
        return client_logic.go_mode(in_logic, slot)

    def tracker_rows(self, show_out_of_logic: bool = True,
                     show_unavailable: bool = False) -> list[tracker.TrackerSection] | None:
        view = tracker.in_logic_view(self)
        if view is None:
            return None
        slot, ap_state, allowed, in_logic = view
        extra = None
        in_logic_ids = None
        if self.achievement_specs:
            in_logic_ids = client_achievements.achievements_in_logic(
                self.achievement_specs, ap_state, slot, in_logic,
                self.achievement_assignments
            )
            extra = tracker.achievement_sections(
                self.achievement_specs, in_logic_ids,
                set(self.missing_locations), show_out_of_logic
            )
        return tracker.tracker_rows(allowed, in_logic,
                                    set(self.missing_locations),
                                    client_logic.slot_value(slot, slot_keys.MISSION_CHECKS),
                                    self.gacha_by_chapter,
                                    show_out_of_logic, show_unavailable,
                                    self.ach_by_chapter, extra, in_logic_ids)

    def inventory_groups(self) -> list[tracker.InventoryGroup] | None:
        slot = self.slot_data
        if slot is None:
            return None
        ap_state = client_logic.ApState.from_item_ids(i.item for i in self.items_received)
        found = len(self.checked_locations)
        return inventory.inventory_groups(
            ap_state, slot, found, found + len(self.missing_locations)
        )

    def unlocked_partners(self) -> set[int] | None:
        slot = self.slot_data
        if slot is None or not client_logic.partner_logic_on(slot):
            return None
        ap_state = client_logic.ApState.from_item_ids(i.item for i in self.items_received)
        return client_logic.unlocked_partners(ap_state)

    def make_gui(self) -> type[GameManager]:
        ui = super().make_gui()
        ui.base_title = "Archipelago Gotcha Force Client"
        return gui.build_manager(self, ui)

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            self._connect(args.get("slot_data") or {})

    def _connect(self, slot: dict[str, Any]) -> None:
        self.slot_data = slot
        self.goal_sent = False
        plan = enemies.plan_enemies(
            client_logic.slot_value(slot, slot_keys.ENEMY_SEED),
            client_logic.slot_value(slot, slot_keys.ENEMY_RANDOMIZATION),
            client_logic.slot_value(slot, slot_keys.COMMANDER_ACE_BORGS),
            client_logic.slot_value(slot, slot_keys.BOSS_BORGS)
        )
        self.enemy_writes = plan.assignments
        self.queue_edits = queues.custom_queue_plan(plan.inserts, plan.removes)
        self.queue_arena = queues.arena_layout(self.queue_edits)
        self.enemy_byte_writes = self._enemy_byte_writes(slot, plan)
        self._plan_gacha(slot, enemies.inserted_borgs(plan.inserts))
        self._plan_achievements(slot)
        self.chapter_costs = enemies.chapter_costs(self.enemy_writes, plan.inserts)
        self.enemy_writes.update(enemies.assign_partners(
            client_logic.slot_value(slot, slot_keys.ENEMY_SEED),
            client_logic.slot_value(slot, slot_keys.PARTNER_BORGS),
            client_logic.slot_value(slot, slot_keys.PARTNER_ACE_BORGS)
        ))
        self._log_connection(slot, plan)

    @staticmethod
    def _enemy_byte_writes(slot: dict[str, Any], plan: EnemyPlan) -> dict[int, int]:
        seed = client_logic.slot_value(slot, slot_keys.ENEMY_SEED)
        writes = enemies.assign_ai(
            seed, client_logic.slot_value(slot, slot_keys.ENEMY_AI),
            client_logic.slot_value(slot, slot_keys.ENEMY_AI_MINIMUM),
            client_logic.slot_value(slot, slot_keys.ENEMY_AI_MAXIMUM)
        )
        writes.update(enemies.assign_levels(
            seed, client_logic.slot_value(slot, slot_keys.ENEMY_LEVELS),
            client_logic.slot_value(slot, slot_keys.ENEMY_LEVEL_MINIMUM),
            client_logic.slot_value(slot, slot_keys.ENEMY_LEVEL_MAXIMUM)
        ))
        writes.update(plan.flag_writes)
        return writes

    def _plan_gacha(self, slot: dict[str, Any], extra: dict[int, list[int]]) -> None:
        if client_logic.slot_value(slot, slot_keys.GACHA_LOCATIONS):
            self.gacha_map = client_logic.gacha_location_map(self.enemy_writes, slot, extra)
            self.gacha_by_chapter = client_logic.gacha_by_chapter_map(self.enemy_writes, slot, extra)
        else:
            self.gacha_map = {}
            self.gacha_by_chapter = {}

    def _plan_achievements(self, slot: dict[str, Any]) -> None:
        self.achievement_assignments = dict(self.enemy_writes)
        plan = client_achievements.achievement_plan_for_slot(slot, self.achievement_assignments)
        self.achievement_specs = plan.specs
        self.ach_by_chapter = client_achievements.achievements_by_chapter_map(plan.specs)

    def _log_connection(self, slot: dict[str, Any], plan: EnemyPlan) -> None:
        starting = client_logic.slot_value(slot, slot_keys.STARTING_BORG)
        logger.info(f"Connected. Starting borg: {client_logic.borg_name(starting)} | spawns to "
                    f"rewrite: {len(self.enemy_writes)} | "
                    f"AI/level/flag bytes: {len(self.enemy_byte_writes)} | "
                    f"packs: {len(plan.packs)} (custom queues: "
                    f"{sorted(self.queue_edits)}) | pairs: "
                    f"{sorted(plan.pairs)} | gacha locations: "
                    f"{sum(len(v) for v in self.gacha_map.values())}")


async def game_watcher(ctx: GotchaForceContext) -> None:
    guardian = Guardian(ctx)
    hook_warned = False
    failures = _FailureLog()
    while not ctx.exit_event.is_set():
        await _wait_for_tick(ctx)
        if not ctx.dolphin.is_connected():
            hooked = await _hook_dolphin(ctx, hook_warned)
            hook_warned = True
            if not hooked:
                continue
        if not await _find_game(ctx, guardian, hook_warned):
            hook_warned = True
            continue
        hook_warned = False
        try:
            victories = guardian.tick()
        except Exception as exc:
            failures.failed(exc)
            continue
        failures.recovered()
        if victories is None:
            continue
        _log_mission_change(ctx, guardian)
        slot = ctx.slot_data
        if slot is not None and ctx.server is not None:
            await _send_checks(ctx, guardian, victories, slot)


class _FailureLog:
    def __init__(self) -> None:
        self.last_failure: str | None = None
        self.consecutive = 0

    def failed(self, exc: Exception) -> None:
        failure = f"{type(exc).__name__}: {exc}"
        if failure != self.last_failure:
            self.last_failure = failure
            self.consecutive = 1
            logger.warning(f"tick failed: {failure}", exc_info=True)
            return
        self.consecutive += 1
        if self.consecutive % FAILURE_SUMMARY_TICKS == 0:
            logger.warning(f"tick failed: {failure} "
                           f"(x{self.consecutive} in a row)")

    def recovered(self) -> None:
        if self.last_failure is None:
            return
        logger.info(f"tick recovered after {self.consecutive} failure(s).")
        self.last_failure = None
        self.consecutive = 0


async def _wait_for_tick(ctx: GotchaForceContext) -> None:
    try:
        await asyncio.wait_for(ctx.watcher_event.wait(), TICK)
    except TimeoutError:
        pass
    ctx.watcher_event.clear()


async def _hook_dolphin(ctx: GotchaForceContext, hook_warned: bool) -> bool:
    if ctx.dolphin.is_connected():
        return True
    ctx.game_valid = False
    if not hook_warned:
        logger.info("Waiting for Dolphin (with Gotcha Force USA "
                    "running)...")
    if ctx.dolphin.connect():
        return True
    await asyncio.sleep(HOOK_RETRY)
    return False


async def _find_game(ctx: GotchaForceContext, guardian: Guardian, hook_warned: bool) -> bool:
    game_id = ctx.dolphin.read(addresses.GAME_ID_ADDR, len(addresses.GAME_ID))
    if game_id != addresses.GAME_ID:
        if ctx.game_valid or not hook_warned:
            logger.info(f"The loaded game is not GG4E08 "
                        f"({game_id!r}); waiting.")
        ctx.game_valid = False
        await asyncio.sleep(HOOK_RETRY)
        return False
    if not ctx.game_valid:
        logger.info("Gotcha Force (GG4E08) detected.")
        guardian.on_game_detected()
        ctx.game_valid = True
    return True


def _log_mission_change(ctx: GotchaForceContext, guardian: Guardian) -> None:
    chapter = guardian.current_chapter()
    if chapter is None or chapter == ctx.last_chapter:
        return
    ctx.last_chapter = chapter
    logger.info(f"[mission] chapter {chapter:03d} ({client_logic.chapter_zone_name(chapter)})")


async def _send_checks(ctx: GotchaForceContext, guardian: Guardian,
                       victories: dict[int, int], slot: client_logic.SlotData) -> None:
    ids = client_logic.won_location_ids(
        victories, client_logic.slot_value(slot, slot_keys.MISSION_CHECKS)
    )
    ids |= guardian.gacha_pending
    ids |= guardian.achievement_pending
    new_ids = ids & ctx.missing_locations
    if new_ids:
        await ctx.check_locations(new_ids)
    guardian.gacha_pending -= ctx.checked_locations
    guardian.achievement_pending -= ctx.checked_locations
    if not ctx.goal_sent and client_logic.goal_reached(victories, slot):
        ctx.goal_sent = True
        ctx.finished_game = True
        await ctx.send_msgs([{"cmd": "StatusUpdate",
                              "status": ClientStatus.CLIENT_GOAL}])
        logger.info("Goal completed!")
