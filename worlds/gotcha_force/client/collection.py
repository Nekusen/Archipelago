from __future__ import annotations

import struct
from typing import Final

from CommonClient import logger

from .. import slot_keys
from ..data import addresses
from ..data.borgs import BORGS, G_RED, G_RED_COST, NEO_G_RED, NEO_G_RED_COST
from . import logic as client_logic
from . import state
from .stage import Stage

XP_PER_ITEM: Final = 250

XP_STATE_FIELD: Final = "xp"

COLLECTION_ENTRY_HEAD: Final = struct.Struct(">HBBIII")

FRAGMENT_ENTRY_HEAD: Final = struct.Struct(">HBBI")
FRAGMENT_ENTRY_PADDING: Final = addresses.FRAG_ENTRY - FRAGMENT_ENTRY_HEAD.size - 1

FORCE_INDICES_FORMAT: Final = f">{addresses.FORCE_INDICES}h"


class CollectionStage(Stage):

    def __init__(self) -> None:
        self._last_serial_handed = 0

    def _enforce_collection(self, progress: int, ap_state: client_logic.ApState,
                            slot: client_logic.SlotData) -> None:
        save = self._savedata()
        if save is None:
            return
        borg_count = self.dolphin.read_u16(save + addresses.SAVE_N_BORGS) or 0
        block = self.dolphin.read(save + addresses.SAVE_COLLECTION,
                                  addresses.COLLECTION_ENTRY * addresses.COLLECTION_SLOTS)
        if block is None:
            return
        ids = self._collection_ids(block)
        self._replace_new_game_g_red(save, ids, borg_count,
                                     client_logic.slot_value(slot, slot_keys.STARTING_BORG))
        desired = client_logic.desired_borgs(
            ap_state, client_logic.slot_value(slot, slot_keys.BOX_BORGS) or ()
        )
        self._upgrade_to_neo_g_red(save, ids, desired)
        self._add_missing_borgs(save, block, ids, borg_count,
                                [b for b in sorted(desired) if b not in ids])
        self._refresh_force_costs(save, ids)
        self._enforce_fragments(block, ap_state)
        self._apply_xp(save, ids, ap_state)

    @staticmethod
    def _collection_ids(block: bytes) -> list[int]:
        return [struct.unpack_from(">H", block, addresses.COLLECTION_ENTRY * entry)[0]
                for entry in range(addresses.COLLECTION_SLOTS)]

    def _replace_new_game_g_red(self, save: int, ids: list[int], borg_count: int,
                                starting: int) -> None:
        if starting != G_RED and borg_count >= 1 and ids[addresses.NEW_GAME_ENTRY] == G_RED:
            self.dolphin.write_u16(save + addresses.SAVE_COLLECTION, starting)
            ids[addresses.NEW_GAME_ENTRY] = starting

    def _upgrade_to_neo_g_red(self, save: int, ids: list[int], desired: set[int]) -> None:
        if NEO_G_RED not in desired or NEO_G_RED in ids or G_RED not in ids:
            return
        entry = ids.index(G_RED)
        offset = save + addresses.SAVE_COLLECTION + addresses.COLLECTION_ENTRY * entry
        self.dolphin.write_u16(offset, NEO_G_RED)
        self.dolphin.write(offset + addresses.COLLECTION_LEVELS_OFF, bytes(addresses.COLLECTION_LEVELS_LEN))
        self.dolphin.write_u32(offset + addresses.COLLECTION_EXP_OFF, 0)
        ids[entry] = NEO_G_RED

    def _add_missing_borgs(self, save: int, block: bytes, ids: list[int],
                           borg_count: int, missing: list[int]) -> None:
        for borg in missing:
            try:
                free_slot = ids.index(addresses.NO_ID)
            except ValueError:
                if borg_count >= addresses.COLLECTION_SLOTS:
                    logger.warning("Collection full: no room for borg "
                                   f"{BORGS[borg].name}")
                    break
                free_slot = borg_count
            offset = save + addresses.SAVE_COLLECTION + addresses.COLLECTION_ENTRY * free_slot
            head = COLLECTION_ENTRY_HEAD.pack(
                borg, addresses.COLLECTION_INITIAL_LEVEL, 0, self._next_serial(block), 0, 0
            )
            self.dolphin.write(offset, head + bytes(addresses.COLLECTION_ENTRY - len(head)))
            self.dolphin.write(offset + addresses.COLLECTION_GACHA_FLAG_OFF, bytes([addresses.OBTAINED_VIA_GACHA]))
            ids[free_slot] = borg
            borg_count = max(borg_count, free_slot + 1)
            self.dolphin.write_u16(save + addresses.SAVE_N_BORGS, borg_count)

    def _next_serial(self, collection_block: bytes) -> int:
        serials = [struct.unpack_from(">I", collection_block,
                                      o + addresses.COLLECTION_SERIAL_OFF)[0]
                   for o in range(0, len(collection_block), addresses.COLLECTION_ENTRY)
                   if not client_logic.is_empty_entry(
                       struct.unpack_from(">H", collection_block, o)[0]
                   )]
        next_serial = (max(serials) + 1) if serials else 0
        self._last_serial_handed = max(self._last_serial_handed, next_serial)
        value = self._last_serial_handed
        self._last_serial_handed += 1
        return value

    def _refresh_force_costs(self, save: int, ids: list[int]) -> None:
        force_count = self.dolphin.read_u16(save + addresses.SAVE_N_FORCES) or 0
        for force_index in range(min(force_count, addresses.FORCE_SLOTS)):
            base = save + addresses.SAVE_FORCES + addresses.FORCE_ENTRY * force_index
            force = self.dolphin.read(base, addresses.FORCE_ENTRY)
            if force is None:
                continue
            indices = struct.unpack_from(FORCE_INDICES_FORMAT, force, addresses.FORCE_INDICES_OFF)
            cost = sum(self._borg_cost(ids[i]) for i in indices
                       if 0 <= i < len(ids))
            current = struct.unpack_from(">I", force, addresses.FORCE_COST_OFF)[0]
            if current != cost:
                self.dolphin.write_u32(base + addresses.FORCE_COST_OFF, cost)

    def _borg_cost(self, borg_id: int) -> int:
        if borg_id in BORGS:
            return BORGS[borg_id].cost
        if borg_id == G_RED:
            return G_RED_COST
        if borg_id == NEO_G_RED:
            return NEO_G_RED_COST
        return 0

    def _enforce_fragments(self, block: bytes, ap_state: client_logic.ApState) -> None:
        box2 = self._box2()
        if box2 is None:
            return
        pending = client_logic.pending_fragments(ap_state)
        if not pending:
            return
        area = self.dolphin.read(box2 + addresses.BOX2_FRAGMENTS,
                                 addresses.FRAG_ENTRY * addresses.FRAG_SLOTS)
        if area is None:
            return
        existing, free_slots = self._fragment_inventory(area)
        total = self.dolphin.read_u16(box2 + addresses.BOX2_N_FRAGMENTS) or 0
        for borg, pieces in sorted(pending.items()):
            owned_pieces = existing.get(borg, set())
            for piece in range(BORGS[borg].fragments):
                if len(owned_pieces) >= pieces:
                    break
                if piece in owned_pieces or not free_slots:
                    continue
                slot_index = free_slots.pop(0)
                offset = box2 + addresses.BOX2_FRAGMENTS + addresses.FRAG_ENTRY * slot_index
                head = FRAGMENT_ENTRY_HEAD.pack(borg, piece, 0, self._next_serial(block))
                self.dolphin.write(offset, head + bytes([addresses.FRAG_NEW_FLAG]) + bytes(FRAGMENT_ENTRY_PADDING))
                owned_pieces.add(piece)
                total += 1
                self.dolphin.write_u16(box2 + addresses.BOX2_N_FRAGMENTS, total)

    @staticmethod
    def _fragment_inventory(area: bytes) -> tuple[dict[int, set[int]], list[int]]:
        existing: dict[int, set[int]] = {}
        free_slots: list[int] = []
        for slot_index in range(addresses.FRAG_SLOTS):
            offset = addresses.FRAG_ENTRY * slot_index
            fragment_id = struct.unpack_from(">H", area, offset)[0]
            if client_logic.is_empty_entry(fragment_id):
                free_slots.append(slot_index)
            else:
                existing.setdefault(fragment_id, set()).add(area[offset + addresses.FRAG_PIECE_OFF])
        return existing, free_slots

    def _apply_xp(self, save: int, ids: list[int], ap_state: client_logic.ApState) -> None:
        ctx = self.ctx
        key = f"{ctx.seed_name}_{ctx.slot}" if ctx.seed_name else None
        if key is None or ap_state.xp_items <= 0:
            return
        applied = state.client_state_get(key, XP_STATE_FIELD, 0)
        new_items = ap_state.xp_items - applied
        if new_items <= 0:
            return
        for entry, borg in enumerate(ids):
            if client_logic.is_empty_entry(borg):
                continue
            offset = (save + addresses.SAVE_COLLECTION + addresses.COLLECTION_ENTRY * entry
                      + addresses.COLLECTION_EXP_OFF)
            exp = self.dolphin.read_u32(offset) or 0
            self.dolphin.write_u32(offset, exp + XP_PER_ITEM * new_items)
        state.client_state_set(key, XP_STATE_FIELD, ap_state.xp_items)
        logger.info(f"Borg Experience applied (+{XP_PER_ITEM * new_items} to the "
                    f"collection)")
