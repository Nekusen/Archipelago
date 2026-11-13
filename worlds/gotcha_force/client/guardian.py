from __future__ import annotations

import struct
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from CommonClient import logger

from .. import iso_patch, slot_keys
from ..data import addresses
from ..data.chapters import CHAPTERS
from ..data.packs import QUEUE2, QUEUE_RECORD
from . import logic as client_logic
from . import queues, stage
from .checks import CheckStage
from .collection import CollectionStage

if TYPE_CHECKING:
    from . import GotchaForceContext


class Guardian(CollectionStage, CheckStage):
    def __init__(self, ctx: GotchaForceContext) -> None:
        self.ctx = ctx
        self.dolphin = ctx.dolphin
        CollectionStage.__init__(self)
        CheckStage.__init__(self)
        self._patch_status: str | None = None
        self._grant_patch: bool | None = None
        self._credit_patch: bool | None = None

    def current_chapter(self) -> int | None:
        progress = self._progress()
        if progress is None:
            return None
        chapter = self.dolphin.read_u32(progress + addresses.OFF_CURRENT_CHAPTER)
        if chapter is None or not (0 < chapter < addresses.N_CHAPTERS):
            return None
        return chapter

    def _progress(self) -> int | None:
        pointer = self.dolphin.read_u32(addresses.G_PROGRESS_PTR)
        return pointer if stage.in_mem1(pointer) else None

    def on_game_detected(self) -> None:
        self._patch_status = None
        self._grant_patch = None
        self._credit_patch = None

    def tick(self) -> dict[int, int] | None:
        ctx = self.ctx
        progress = self._progress()
        if progress is None:
            return None
        self._check_patch()
        if ctx.slot_data is None:
            return None

        ap_state = client_logic.ApState.from_item_ids(i.item for i in ctx.items_received)
        slot = ctx.slot_data

        states = self.dolphin.read(progress + addresses.OFF_CHAPTER_STATE,
                                   addresses.CHAPTER_STATE_STRIDE * addresses.N_CHAPTERS)
        if states is None:
            return None
        victories = self._victories(states)

        self._watch_battle()
        self._detect_achievements(slot, victories)

        self._write_player_state(progress, ap_state, slot)
        self._write_starting_borg(slot)
        self._revert_story_flags(progress)
        self._clear_map_staging(progress)

        allowed = client_logic.allowed_chapters(ap_state, slot)
        ctx.last_allowed = allowed
        self._publish_chapter_states(progress, states, allowed)
        self._refresh_map_caches(progress, allowed)
        self._write_hud_tables(ap_state, slot, allowed, victories)
        self._write_tints()

        self._enforce_collection(progress, ap_state, slot)
        self._enforce_enemies()
        self._gacha_tick(progress, slot)

        return {c: v for c, v in victories.items() if v}

    def _check_patch(self) -> None:
        if self._patch_status is not None:
            return
        status = iso_patch.patch_status_in_memory(self.dolphin.read)
        self._grant_patch = status.words.get(addresses.GACHA_GRANT_HOOK)
        self._credit_patch = status.words.get(addresses.GACHA_CREDIT_HOOK)
        if status.status is None:
            return
        self._patch_status = status.status
        if status.status == iso_patch.PATCH_CURRENT:
            logger.info("Patched ISO detected: the on-map mission status "
                        "display is active.")
        elif status.status == iso_patch.PATCH_NONE:
            logger.warning(
                "This ISO does not have the Archipelago patch: the on-map "
                "mission status display will not show, and some gacha "
                "features fall back to the original game behaviour. To "
                'fix it, open the Archipelago Launcher, run "Gotcha Force '
                'ISO Patcher" on your clean USA ISO and play the '
                '" [AP]" copy it creates. Your progress and checks are '
                "not affected."
            )
        else:
            logger.warning(
                "Your patched ISO was made with an older version of this "
                "apworld: some features may look broken or be missing. "
                "To update it, open the Archipelago Launcher and run "
                '"Gotcha Force ISO Patcher" on your clean USA ISO again; '
                'the " [AP]" copy is refreshed in place. Your progress '
                "and checks are not affected."
            )

    @staticmethod
    def _victories(states: bytes) -> dict[int, int]:
        return {c: states[addresses.CHAPTER_STATE_STRIDE * c + addresses.CHAPTER_STATE_WINS]
                for c in range(addresses.N_CHAPTERS)}

    def _write_player_state(self, progress: int, ap_state: client_logic.ApState,
                            slot: client_logic.SlotData) -> None:
        cap = client_logic.gf_cap_value(ap_state, client_logic.slot_value(slot, slot_keys.STARTING_BORG_COST))
        self._write_u32_if_diff(progress + addresses.OFF_GF_CAP, cap)
        self._write_u32_if_diff(progress + addresses.OFF_GF_CURRENT, cap)
        self._write_u32_if_diff(progress + addresses.OFF_COMPANIONS, client_logic.companion_bits(ap_state))
        levels = client_logic.upgrade_levels(ap_state, client_logic.slot_value(slot, slot_keys.COMMANDER_ITEMS))
        self._write_if_diff(progress + addresses.OFF_UPGRADES, levels)
        self._write_u32_if_diff(progress + addresses.OFF_ZONES, addresses.ZONES_ALL_MASK)
        self._write_u32_if_diff(progress + addresses.OFF_BOX_FLAG,
                                addresses.BOX_UNLOCKED if ap_state.gotcha_box else addresses.BOX_LOCKED)

    def _write_u32_if_diff(self, addr: int, value: int) -> None:
        self._write_if_diff(addr, struct.pack(">I", value))

    def _write_starting_borg(self, slot: client_logic.SlotData) -> None:
        starting = client_logic.slot_value(slot, slot_keys.STARTING_BORG)
        self._write_if_diff(addresses.INITIAL_FORCE_TABLE,
                            struct.pack(">H", starting) + addresses.NO_ID_BYTES)
        self._write_if_diff(addresses.AP_STORY_BORG, struct.pack(">H", starting))

    def _revert_story_flags(self, progress: int) -> None:
        flags = self.dolphin.read(progress + addresses.OFF_FLAGS64, addresses.FLAGS64_LEN)
        if flags is None:
            return
        desired = bytearray(addresses.FLAGS64_LEN)
        desired[::addresses.STORY_FLAG_STRIDE] = bytes(
            flag & addresses.STORY_FLAG_PLAYED for flag in flags[::addresses.STORY_FLAG_STRIDE]
        )
        if flags != bytes(desired):
            self.dolphin.write(progress + addresses.OFF_FLAGS64, bytes(desired))

    def _clear_map_staging(self, progress: int) -> None:
        self._write_if_diff(progress + addresses.OFF_MAP_STAGING,
                            bytes(addresses.MAP_STAGING_ARRAYS * addresses.MAP_STAGING_LEN))
        route = (self.dolphin.read_u32(progress + addresses.OFF_ROUTE) or 0) & addresses.ROUTE_MASK
        self._write_if_diff(progress + addresses.OFF_PERSISTENT + route * addresses.PERSISTENT_LEN,
                            bytes(addresses.PERSISTENT_LEN))

    def _publish_chapter_states(self, progress: int, states: bytes, allowed: set[int]) -> None:
        for chapter in range(addresses.N_CHAPTERS):
            current = states[addresses.CHAPTER_STATE_STRIDE * chapter]
            desired = ((current & ~(addresses.CHAPTER_AVAILABLE | addresses.CHAPTER_WON))
                       | (addresses.CHAPTER_AVAILABLE if chapter in allowed else 0))
            if current != desired:
                self.dolphin.write(progress + addresses.OFF_CHAPTER_STATE
                                   + addresses.CHAPTER_STATE_STRIDE * chapter, bytes([desired]))

    def _refresh_map_caches(self, progress: int, available: set[int]) -> None:
        by_tile: dict[int, list[int]] = {}
        for chapter in available:
            chapter_data = CHAPTERS.get(chapter)
            if chapter_data is not None:
                by_tile.setdefault(chapter_data.tile, []).append(chapter)
        slots = addresses.MAP_TILE_SLOTS
        for tile in range(addresses.MAP_TILES):
            chapters = sorted(by_tile.get(tile, []))[:slots]
            self.dolphin.write(progress + addresses.OFF_MAP_COUNTS + tile, bytes([len(chapters)]))
            self.dolphin.write(progress + addresses.OFF_MAP_LISTS + slots * tile,
                               _zero_padded(chapters, slots))
            self.dolphin.write(progress + addresses.OFF_MAP_MAJORS + slots * tile,
                               _zero_padded((CHAPTERS[c].major & addresses.BYTE_MASK for c in chapters), slots))

    def _write_hud_tables(self, ap_state: client_logic.ApState, slot: client_logic.SlotData,
                          allowed: set[int], victories: dict[int, int]) -> None:
        ctx = self.ctx
        in_logic = client_logic.chapters_in_logic_for_slot(
            ap_state, slot, allowed, ctx.chapter_costs, client_logic.gf_ratio_for_slot(slot)
        )
        table = bytearray(addresses.AP_TABLE_LEN)
        flags = bytearray(addresses.AP_FLAGS_LEN)
        slot_ids = ((set(ctx.checked_locations) | set(ctx.missing_locations))
                    if ctx.server is not None else None)
        for chapter in allowed:
            if chapter >= addresses.AP_FLAGS_LEN:
                continue
            if slot_ids is not None:
                done, total = self._chapter_counts(slot, chapter, slot_ids)
                table[chapter * addresses.AP_TABLE_ENTRY] = done
                table[chapter * addresses.AP_TABLE_ENTRY + addresses.AP_TABLE_TOTAL_OFF] = total
            flags[chapter] = ((addresses.AP_FLAG_DONE if victories.get(chapter, 0) else 0)
                              | (addresses.AP_FLAG_OUT_OF_LOGIC if chapter not in in_logic else 0))
        self._write_if_diff(addresses.AP_TABLE, bytes(table))
        self._write_if_diff(addresses.AP_FLAGS, bytes(flags))

    def _chapter_counts(self, slot: client_logic.SlotData, chapter: int,
                        slot_ids: set[int]) -> tuple[int, int]:
        ctx = self.ctx
        ids = client_logic.chapter_check_ids(
            chapter, client_logic.slot_value(slot, slot_keys.MISSION_CHECKS),
            ctx.gacha_by_chapter, ctx.ach_by_chapter
        ) & slot_ids
        done = len(ids & set(ctx.checked_locations))
        return min(done, addresses.AP_TABLE_MAX_COUNT), min(len(ids), addresses.AP_TABLE_MAX_COUNT)

    def _write_tints(self) -> None:
        self._write_if_diff(addresses.AP_TINTS, addresses.AP_TINTS_BYTES)

    def _enforce_enemies(self) -> None:
        word_writes = self.ctx.enemy_writes
        byte_writes = self.ctx.enemy_byte_writes
        if not word_writes and not byte_writes:
            return
        first = min(list(word_writes) + list(byte_writes))
        end = max([a + addresses.U16_SIZE for a in word_writes] + [a + 1 for a in byte_writes])
        block = self.dolphin.read(first, end - first)
        if block is None:
            return
        for addr, value in word_writes.items():
            if value is None:
                continue
            offset = addr - first
            if struct.unpack(">H", block[offset:offset + addresses.U16_SIZE])[0] != value:
                self.dolphin.write_u16(addr, value)
        for addr, value in byte_writes.items():
            if block[addr - first] != value:
                self.dolphin.write(addr, bytes([value]))
        self._enforce_queues(word_writes, byte_writes)

    def _enforce_queues(self, word_writes: Mapping[int, int | None], byte_writes: dict[int, int]) -> None:
        for chapter, edit in self.ctx.queue_edits.items():
            vanilla = QUEUE2[chapter]
            queue = self.dolphin.read(vanilla.pointer, vanilla.records * QUEUE_RECORD)
            if queue is None:
                continue
            blob = queues.queue_with_inserts(
                queues.apply_overrides(queue, vanilla.pointer, word_writes, byte_writes), vanilla.pointer,
                edit.inserts, edit.removes
            )
            dest = self.ctx.queue_arena[chapter]
            if self.dolphin.read(dest, len(blob)) != blob:
                self.dolphin.write(dest, blob)
            entry = queues.stage_table_entry(chapter)
            if self.dolphin.read_u32(entry) != dest:
                self.dolphin.write_u32(entry, dest)

def _zero_padded(values: Iterable[int], length: int) -> bytes:
    data = bytes(values)
    return data + bytes(length - len(data))
