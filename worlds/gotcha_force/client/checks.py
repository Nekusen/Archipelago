from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Final

from CommonClient import logger

from .. import slot_keys
from ..data import addresses
from ..data.borgs import BORGS
from ..data.companions import COMPANIONS
from ..data.gacha import (
    GACHA_PRIZE_MODE_BYTE,
    GACHA_RECORD_LEN,
    GACHA_REGISTERS,
    GACHA_SUPPRESS_MODE,
    GACHA_THRESHOLDS_OFF,
    THRESHOLD_COUNT,
)
from ..logic import achievements, gacha
from ..logic.gacha import EXHAUSTED, UNSCALED_RATE
from . import achievements as client_achievements
from . import logic as client_logic
from . import stage
from .stage import Stage

NO_PARTNER_LABEL: Final = "none"

THRESHOLDS: Final = struct.Struct(f">{THRESHOLD_COUNT}h")

PLAYER_BATTLE_SLOT: Final = 0


@dataclass
class BattleSnapshot:
    entity_ptrs: list[int]
    own_losses: int | None


@dataclass
class BattleResult:
    finisher_slot: int | None
    own_losses: int | None


class CheckStage(Stage):
    _grant_patch: bool | None

    def __init__(self) -> None:
        self.gacha_pending: set[int] = set()
        self.achievement_pending: set[int] = set()
        self._prev_victories: dict[int, int] | None = None
        self._battle_snapshot: BattleSnapshot | None = None
        self._battle_result: BattleResult | None = None
        self._gacha_prev: int | None = None
        self._gacha_saved_count: int | None = None

    def _watch_battle(self) -> None:
        if not self.ctx.achievement_specs:
            return
        battle = self._battle()
        if battle is None:
            return
        resolution = self.dolphin.read(battle + addresses.OFF_BATTLE_RESOLUTION, 1)
        if resolution is None:
            return
        if resolution[0] == addresses.BATTLE_UNRESOLVED:
            self._snapshot_battle()
        elif self._battle_snapshot is not None and self._battle_result is None:
            self._freeze_battle_result(battle, self._battle_snapshot)

    def _battle(self) -> int | None:
        pointer = self.dolphin.read_u32(addresses.BATTLE_PTR)
        return pointer if stage.in_mem1(pointer) else None

    def _snapshot_battle(self) -> None:
        entity_ptrs = [
            self.dolphin.read_u32(addresses.SLOT_ENTITY_PTRS + addresses.POINTER_SIZE * slot) or 0
            for slot in range(addresses.BATTLE_SLOTS)
        ]
        player_entity = entity_ptrs[PLAYER_BATTLE_SLOT]
        if not stage.in_mem1(player_entity):
            return
        self._battle_snapshot = BattleSnapshot(entity_ptrs, self._own_losses(player_entity))
        self._battle_result = None

    def _own_losses(self, player_entity: int) -> int | None:
        if not stage.in_mem1(player_entity):
            return None
        losses = self.dolphin.read(player_entity + addresses.OFF_ENT_OWN_LOSSES, 1)
        return losses[0] if losses else None

    def _freeze_battle_result(self, battle: int, snapshot: BattleSnapshot) -> None:
        finisher = self.dolphin.read_u32(battle + addresses.OFF_BATTLE_FINISHER) or 0
        losses = self._own_losses(snapshot.entity_ptrs[PLAYER_BATTLE_SLOT])
        self._battle_result = BattleResult(
            finisher_slot=snapshot.entity_ptrs.index(finisher) if finisher in snapshot.entity_ptrs else None,
            own_losses=losses if losses is not None else snapshot.own_losses,
        )

    def _detect_achievements(self, slot: client_logic.SlotData, victories: dict[int, int]) -> None:
        ctx = self.ctx
        specs = ctx.achievement_specs
        if not specs:
            return
        prev, self._prev_victories = self._prev_victories, dict(victories)
        if prev is None:
            return
        newly_won = [c for c, v in victories.items() if v > prev.get(c, 0)]
        if not newly_won:
            return
        partner = self._read_battle_partner()
        force_ids, cost = self._read_battle_force()
        minimum = int(client_logic.slot_value(slot, slot_keys.TRIBE_FORCE_MIN_COST))
        result = self._battle_result or BattleResult(None, None)
        names = [client_logic.borg_name(i) if i in BORGS else f"{i:#06x}" for i in force_ids]
        for chapter in newly_won:
            earned = achievements.achievements_met(
                specs,
                chapter,
                partner,
                force_ids,
                cost,
                minimum,
                finisher_slot=result.finisher_slot,
                own_losses=result.own_losses,
            )
            logger.info(
                f"[achievement] Chapter {chapter:03d} won with partner "
                f"{COMPANIONS.get(partner, NO_PARTNER_LABEL)} and force "
                f"{names} (cost {cost}): {len(earned)} check(s)"
            )
            for spec in earned:
                self.achievement_pending.add(client_achievements.achievement_id(spec))

    def _read_battle_partner(self) -> int:
        battle = self._battle()
        if battle is None:
            return 0
        teams = self.dolphin.read(battle + addresses.OFF_BATTLE_SLOT_TEAM, addresses.BATTLE_SLOTS)
        quotas = self.dolphin.read(battle + addresses.OFF_BATTLE_QUOTA, addresses.BATTLE_SLOTS)
        commanders = self.dolphin.read(battle + addresses.OFF_BATTLE_COMMANDER, addresses.BATTLE_SLOTS)
        if teams is None or quotas is None or commanders is None:
            return 0
        for slot in range(addresses.BATTLE_SLOTS):
            if (
                teams[slot] == addresses.TEAM_PLAYER_SIDE
                and quotas[slot] > 0
                and addresses.FIRST_COMMANDER <= commanders[slot] <= addresses.N_COMMANDERS
            ):
                return commanders[slot]
        return 0

    def _read_battle_force(self) -> tuple[list[int], int]:
        battle = self._battle()
        if battle is None:
            return [], 0
        cost = self.dolphin.read_u32(battle + addresses.OFF_BATTLE_ALLY_METER) or 0
        quota = self.dolphin.read(battle + addresses.OFF_BATTLE_QUOTA, 1)
        deployed = quota[0] if quota else 0
        if not (1 <= deployed <= addresses.BATTLE_FORCE_SLOTS):
            return [], cost
        raw = self.dolphin.read(battle + addresses.OFF_BATTLE_FORCE, addresses.BATTLE_FORCE_ENTRY * deployed)
        if raw is None:
            return [], cost
        ids = [struct.unpack_from(">H", raw, i * addresses.BATTLE_FORCE_ENTRY)[0] for i in range(deployed)]
        return [borg_id for borg_id in ids if borg_id != addresses.NO_ID], cost

    def _gacha_tick(self, progress: int, slot: client_logic.SlotData) -> None:
        rate = client_logic.slot_value(slot, slot_keys.GACHA_RATE)
        active = bool(client_logic.slot_value(slot, slot_keys.GACHA_LOCATIONS))
        self._write_gacha_switches(slot, active)
        if not active and rate <= UNSCALED_RATE:
            return
        if not self._write_thresholds(active, rate):
            return
        if not active:
            return
        self._suppress_grant_without_patch()
        self._detect_prize(progress)
        self._restore_accumulators(progress)

    def _write_gacha_switches(self, slot: client_logic.SlotData, active: bool) -> None:
        self._write_if_diff(addresses.AP_GACHA_SUPPRESS, addresses.SWITCH_ON if active else addresses.SWITCH_OFF)
        credit = bool(client_logic.slot_value(slot, slot_keys.GACHA_PARTNER_KILLS))
        self._write_if_diff(addresses.AP_GACHA_CREDIT, addresses.SWITCH_ON if credit else addresses.SWITCH_OFF)

    def _write_thresholds(self, active: bool, rate: int) -> bool:
        base = min(register.address for register in GACHA_REGISTERS.values())
        table = self.dolphin.read(base, GACHA_RECORD_LEN * len(GACHA_REGISTERS))
        if table is None:
            return False
        owned = None if active else self._owned_borgs()
        for borg, register in GACHA_REGISTERS.items():
            target = self._target_thresholds(borg, register.thresholds, rate, owned)
            thresholds_address = register.address + GACHA_THRESHOLDS_OFF
            current = THRESHOLDS.unpack_from(table, thresholds_address - base)
            if current != tuple(target):
                self.dolphin.write(thresholds_address, THRESHOLDS.pack(*target))
        return True

    def _owned_borgs(self) -> set[int]:
        owned: set[int] = set()
        save = self._savedata()
        if save is not None:
            owned |= self._read_ids(
                save + addresses.SAVE_COLLECTION, addresses.COLLECTION_ENTRY, addresses.COLLECTION_SLOTS
            )
        box2 = self._box2()
        if box2 is not None:
            owned |= self._read_ids(box2 + addresses.BOX2_OVERFLOW, addresses.OVERFLOW_ENTRY, addresses.OVERFLOW_SLOTS)
        return owned

    def _read_ids(self, addr: int, entry_len: int, slots: int) -> set[int]:
        block = self.dolphin.read(addr, entry_len * slots)
        if not block:
            return set()
        ids = {struct.unpack_from(">H", block, entry_len * entry)[0] for entry in range(slots)}
        return {borg_id for borg_id in ids if not client_logic.is_empty_entry(borg_id)}

    def _target_thresholds(
        self, borg: int, vanilla: tuple[int, ...], rate: int, owned: set[int] | None
    ) -> tuple[int, ...]:
        if owned is not None:
            return vanilla if borg in owned else gacha.thresholds_for(borg, vanilla, rate)
        locations = self.ctx.gacha_map.get(borg)
        if not locations or all(
            location in self.ctx.checked_locations or location in self.gacha_pending for location in locations
        ):
            return EXHAUSTED
        return gacha.thresholds_for(borg, vanilla, rate)

    def _suppress_grant_without_patch(self) -> None:
        if self._grant_patch is not False:
            return
        mode = self.dolphin.read(GACHA_PRIZE_MODE_BYTE, 1)
        if mode is not None and mode[0] != GACHA_SUPPRESS_MODE:
            self.dolphin.write(GACHA_PRIZE_MODE_BYTE, bytes([GACHA_SUPPRESS_MODE]))

    def _detect_prize(self, progress: int) -> None:
        whole_count = self.dolphin.read_u32(progress + addresses.OFF_GACHA_WHOLE_COUNT) or 0
        piece_count = self.dolphin.read_u32(progress + addresses.OFF_GACHA_PIECE_COUNT) or 0
        total = whole_count + piece_count
        if self._gacha_prev is None:
            self._gacha_prev = total
            return
        if total <= self._gacha_prev:
            return
        self._gacha_prev = total
        borg = self.dolphin.read_u16(progress + addresses.OFF_GACHA_PRIZE_LATCH)
        if borg is not None:
            self._register_prize(borg)
        if self._gacha_saved_count is None:
            accumulators = self.dolphin.read_u32(progress + addresses.OFF_GACHA_ACCUMULATORS)
            if accumulators:
                self._gacha_saved_count = accumulators
                self.dolphin.write_u32(progress + addresses.OFF_GACHA_ACCUMULATORS, 0)

    def _register_prize(self, borg: int) -> None:
        for location in self.ctx.gacha_map.get(borg, []):
            if location not in self.ctx.checked_locations and location not in self.gacha_pending:
                self.gacha_pending.add(location)
                logger.info(f"[gacha] {BORGS[borg].name}: check")
                break

    def _restore_accumulators(self, progress: int) -> None:
        if self._gacha_saved_count is None:
            return
        screen = self.dolphin.read_u32(progress + addresses.OFF_SCREEN)
        if screen != addresses.SCREEN_RESULTS:
            self.dolphin.write_u32(progress + addresses.OFF_GACHA_ACCUMULATORS, self._gacha_saved_count)
            self._gacha_saved_count = None
