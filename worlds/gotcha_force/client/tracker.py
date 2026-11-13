from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Final, NamedTuple

from .. import slot_keys
from ..data.chapters import CHAPTERS
from ..data.titles import TITLES
from ..data.zones import ZONES
from ..locations import ACHIEVEMENT_PREFIX, CHECK_NAME_PREFIX, GACHA_PREFIX
from ..logic import achievements, progression
from ..logic.achievements import Spec
from . import achievements as achievements_client
from . import logic as client_logic
from .logic import (
    LOCATION_ID_TO_NAME,
    SLOT_DEFAULTS,
    ApState,
    SlotData,
)

if TYPE_CHECKING:
    from . import GotchaForceContext

ROW_IN_LOGIC: Final = 0
ROW_OUT_OF_LOGIC: Final = 1
ROW_UNAVAILABLE: Final = 2

OUT_OF_LOGIC_MARK: Final = "  [out of logic]"

LINE_HAVE: Final = 0
LINE_MISSING: Final = 1
LINE_INFO: Final = 2

_ORDER_MISSION: Final = 0
_ORDER_OTHER: Final = 1
_ORDER_GACHA: Final = 2

ACHIEVEMENT_TILE: Final = -1
ACHIEVEMENT_SECTION_TITLE: Final = "Achievements"

FREE_ACHIEVEMENT_TYPES: Final = (
    achievements.TYPE_PARTNER_STYLE,
    achievements.TYPE_COMMANDER_STYLE,
    achievements.TYPE_TRIBE_FORCE,
    achievements.TYPE_ACE_DUEL,
)

GO_MODE_GREEN: Final = "20ff20"
GO_MODE_RED: Final = "cf1010"


class InventoryGroup(NamedTuple):
    key: str
    title: str
    open: bool
    lines: tuple[tuple[int, str], ...]


class MissionRow(NamedTuple):
    chapter: int | str
    state: int
    names: list[str]


class TrackerSection(NamedTuple):
    tile: int
    title: str
    rows: list[MissionRow]


def in_logic_view(
    ctx: GotchaForceContext,
) -> tuple[SlotData, ApState, set[int], set[int]] | None:
    slot = ctx.slot_data
    allowed = ctx.last_allowed
    if slot is None or allowed is None:
        return None
    ap_state = ApState.from_item_ids(i.item for i in ctx.items_received)
    in_logic = client_logic.chapters_in_logic_for_slot(
        ap_state, slot, allowed, ctx.chapter_costs, client_logic.gf_ratio_for_slot(slot)
    )
    return slot, ap_state, allowed, in_logic


def partner_hint(chapter: int, unlocked: Iterable[int]) -> str:
    if progression.partner_requirement_met(chapter, unlocked):
        return ""
    return f"needs {progression.partner_label(chapter)}"


def chapter_label(chapter: int | str) -> str:
    if isinstance(chapter, str):
        return chapter
    title = TITLES.get(chapter)
    return f"{chapter:03d} - {title}" if title else f"{chapter:03d}"


def row_count(names: Iterable[str]) -> int:
    return sum(1 for n in names if not n.endswith(OUT_OF_LOGIC_MARK))


def hide_gacha_spoilers(names: list[str]) -> list[str]:
    gacha = sum(1 for n in names if n.startswith(GACHA_PREFIX))
    if not gacha:
        return names
    return [n for n in names if not n.startswith(GACHA_PREFIX)] + [gacha_summary(gacha)]


def gacha_summary(count: int) -> str:
    return f"Gacha: {count} check{'s' if count != 1 else ''} left"


def tracker_rows(
    allowed: set[int],
    in_logic: set[int],
    missing: set[int],
    checks: int = SLOT_DEFAULTS[slot_keys.MISSION_CHECKS],
    gacha_by_chapter: Mapping[int, set[int]] | None = None,
    show_out_of_logic: bool = True,
    show_unavailable: bool = False,
    ach_by_chapter: Mapping[int, set[int]] | None = None,
    extra_sections: list[TrackerSection] | None = None,
    ach_in_logic: set[int] | None = None,
) -> list[TrackerSection]:
    hidden = {ROW_OUT_OF_LOGIC} if not show_out_of_logic else set()
    if not show_unavailable:
        hidden.add(ROW_UNAVAILABLE)
    sections: list[TrackerSection] = []
    for tile in sorted(ZONES):
        missions: list[MissionRow] = []
        for chapter in sorted(c for c in CHAPTERS if CHAPTERS[c].tile == tile):
            state = _row_state(chapter, allowed, in_logic)
            if state in hidden:
                continue
            ids = client_logic.chapter_check_ids(chapter, checks, gacha_by_chapter, ach_by_chapter) & missing
            anchored = ach_by_chapter.get(chapter, set()) if ach_by_chapter else set()
            row = _mission_row(
                chapter, state, ids, anchored, ach_in_logic if ach_by_chapter else None, show_out_of_logic
            )
            if row is not None:
                missions.append(row)
        if missions:
            sections.append(TrackerSection(tile, ZONES[tile], missions))
    if extra_sections:
        sections.extend(section for section in extra_sections if section.rows)
    return sections


def _row_state(chapter: int, allowed: set[int], in_logic: set[int]) -> int:
    if chapter in in_logic:
        return ROW_IN_LOGIC
    if chapter in allowed:
        return ROW_OUT_OF_LOGIC
    return ROW_UNAVAILABLE


def _mission_row(
    chapter: int, state: int, ids: set[int], anchored: set[int], ach_in_logic: set[int] | None, show_out_of_logic: bool
) -> MissionRow | None:
    out_of_logic: set[int] = set()
    if ach_in_logic is not None and state == ROW_IN_LOGIC:
        out_of_logic = (anchored & ids) - ach_in_logic
        if not show_out_of_logic:
            ids -= out_of_logic
            out_of_logic = set()
        elif ids and out_of_logic == ids:
            state = ROW_OUT_OF_LOGIC
            out_of_logic = set()
    if not ids:
        return None
    return MissionRow(chapter, state, _row_names(ids, out_of_logic))


def _row_names(ids: set[int], out_of_logic: set[int]) -> list[str]:
    marked = {LOCATION_ID_TO_NAME[i] for i in out_of_logic}
    return [
        n + OUT_OF_LOGIC_MARK if n in marked else n
        for n in sorted((LOCATION_ID_TO_NAME[i] for i in ids), key=_tracker_order)
    ]


def _tracker_order(name: str) -> tuple[int, str]:
    if name.startswith(CHECK_NAME_PREFIX):
        kind = _ORDER_MISSION
    elif name.startswith(GACHA_PREFIX):
        kind = _ORDER_GACHA
    else:
        kind = _ORDER_OTHER
    return kind, name


def achievement_sections(
    specs: Iterable[Spec],
    in_logic_ids: set[int],
    missing: set[int],
    show_out_of_logic: bool = True,
) -> list[TrackerSection]:
    by_kind: dict[str, list[tuple[str, bool]]] = {kind: [] for kind in FREE_ACHIEVEMENT_TYPES}
    for raw_spec in specs:
        spec = achievements.as_spec(raw_spec)
        if spec.kind not in by_kind:
            continue
        location_id = achievements_client.achievement_id(spec)
        if location_id not in missing:
            continue
        by_kind[spec.kind].append((LOCATION_ID_TO_NAME[location_id], location_id in in_logic_ids))
    rows: list[MissionRow] = []
    for kind in FREE_ACHIEVEMENT_TYPES:
        members = sorted(by_kind[kind])
        if not members:
            continue
        row = _achievement_row(members, show_out_of_logic)
        if row is not None:
            rows.append(row)
    return [TrackerSection(ACHIEVEMENT_TILE, ACHIEVEMENT_SECTION_TITLE, rows)] if rows else []


def _achievement_row(members: list[tuple[str, bool]], show_out_of_logic: bool) -> MissionRow | None:
    title = achievement_group(members[0][0])
    if any(ok for _name, ok in members):
        if show_out_of_logic:
            names = [name if ok else name + OUT_OF_LOGIC_MARK for name, ok in members]
        else:
            names = [name for name, ok in members if ok]
        return MissionRow(title, ROW_IN_LOGIC, names)
    if not show_out_of_logic:
        return None
    return MissionRow(title, ROW_OUT_OF_LOGIC, [name for name, _ok in members])


def achievement_group(name: str) -> str:
    return name.removeprefix(ACHIEVEMENT_PREFIX).split(":", 1)[0]
