from __future__ import annotations

import dataclasses
import random
from collections.abc import Mapping, Sequence
from typing import NamedTuple

from ..data.addresses import NO_ID, QREC_FLAGS, QREC_ID
from ..data.borgs import BORGS, COSTS, RANDOMIZABLE
from ..data.chapters import CHAPTERS, GOAL_CHAPTERS, TUTORIAL_CHAPTER
from ..data.packs import (
    DARK_KNIGHT,
    DARK_KNIGHT_ESCORTS,
    FUSION_PAIRS,
    ISOLATED_WAVES,
    MACHINE_PACK_PAIRS,
    MACHINE_PACKS,
    PACK_DARK_KNIGHT,
    PACK_ESCORT_CELLS,
    PACK_KINDS,
    PACK_LEADER_CELLS,
    QUEUE2,
    QUEUE_RECORD,
    SPAWN_FLAGS,
    Queue,
)
from ..data.partner_forces import PARTNER_FORCES
from ..data.spawns import (
    ACE_ADDRS,
    ALT_FORMS,
    BOSS_ADDRS,
    BOSS_IDS,
    COMMANDER_TARGETS,
    SCENARIO_AI_TARGETS,
    SIGNATURE_BORGS,
    SPAWN_COSTS,
    SPAWNS,
)

MODE_VANILLA = 0
MODE_BALANCED = 1
MODE_CHAOS = 2

STAT_VANILLA = 0
STAT_PROGRESSIVE = 1
STAT_RANDOM = 2

SPECIAL_VANILLA = 0
SPECIAL_SHUFFLE = 1
SPECIAL_RANDOM = 2

BOSS_VANILLA = 0
BOSS_ROSTER = 1
BOSS_FULL_RANDOM = 2

PARTNER_VANILLA = 0
PARTNER_BALANCED = 1
PARTNER_RANDOM = 2

_SALT_SHIFT = 4
_SALT_BOSS = 0xB055
_SALT_ACE = 0xACE
_SALT_PARTNER = 0x9A27
_SALT_ESCORT = 0xE5C0
_SALT_AI = 0xA1
_SALT_LEVEL = 0x1E

_MAX_SPHERE = max(ch.sphere for ch in CHAPTERS.values())

_ACE_CELLS = frozenset(a for v in ACE_ADDRS.values() for a in v)
_BOSS_CELLS = frozenset(BOSS_ADDRS)
_PACK_CELLS = frozenset(PACK_LEADER_CELLS) | frozenset(a for v in PACK_ESCORT_CELLS.values() for a in v)
_SPECIAL_CELLS = _ACE_CELLS | _BOSS_CELLS | _PACK_CELLS

_VANILLA_ID: dict[int, int | None] = {spawn.cell: spawn.borg for rows in SPAWNS.values() for spawn in rows}
_CELL_CHAPTER: dict[int, int] = {spawn.cell: chapter for chapter, rows in SPAWNS.items() for spawn in rows}

_CANDIDATES: tuple[int, ...] = RANDOMIZABLE

MIN_BALANCED_COST = 10
BALANCED_COST_FACTOR = 2

PROGRESSIVE_NOISE = (-1, 0, 0, 0, 1)

PARTNER_BUDGET_PICK_MIN_FACTOR = 0.5
PARTNER_BUDGET_PICK_MAX_FACTOR = 1.6
PARTNER_BUDGET_EXHAUSTED_BELOW = 10

MACHINE_ESCORT_CAP = 1
MACHINE_PAIR_ESCORTS = 1
_MACHINE_INSERT_DPOS = (0.0, 0.0, 200.0)

NO_BURST_BIT = 0x40

FLAGS_OFF = QREC_FLAGS - QREC_ID

PROTECTED_CHAPTERS = frozenset(GOAL_CHAPTERS) | frozenset({TUTORIAL_CHAPTER})


class _StatTarget(NamedTuple):
    salt: int
    cell_field: str
    keep_mask: int


AI_TARGET = _StatTarget(_SALT_AI, "ai_cell", 0xF0)
LEVEL_TARGET = _StatTarget(_SALT_LEVEL, "level_cell", 0x00)


@dataclasses.dataclass(frozen=True)
class Escort:
    borg: int
    cap: int
    flags: int | None
    dpos: tuple[float, float, float]


@dataclasses.dataclass
class EnemyPlan:
    assignments: dict[int, int | None] = dataclasses.field(default_factory=dict)
    flag_writes: dict[int, int] = dataclasses.field(default_factory=dict)
    inserts: dict[int, tuple[Escort, ...]] = dataclasses.field(default_factory=dict)
    removes: set[int] = dataclasses.field(default_factory=set)
    packs: dict[int, int] = dataclasses.field(default_factory=dict)
    pairs: dict[int, tuple[int, int]] = dataclasses.field(default_factory=dict)


def assign_ai(seed: int, mode: int, lo: int, hi: int) -> dict[int, int]:
    return _assign_stat(seed, AI_TARGET, mode, lo, hi)


def _assign_stat(seed: int, target: _StatTarget, mode: int, low: int, high: int) -> dict[int, int]:
    if mode == STAT_VANILLA:
        return {}
    rng = _stream(seed, target.salt)
    out: dict[int, int] = {}
    for chapter in sorted(SCENARIO_AI_TARGETS):
        if chapter in PROTECTED_CHAPTERS:
            continue
        sphere = CHAPTERS[chapter].sphere
        for row in SCENARIO_AI_TARGETS[chapter]:
            out[getattr(row, target.cell_field)] = _roll_stat(rng, mode, low, high, sphere)
    for participant in COMMANDER_TARGETS:
        sphere = CHAPTERS[participant.latest_chapter].sphere
        value = _roll_stat(rng, mode, low, high, sphere)
        if target is AI_TARGET:
            out[participant.ai_cell] = (participant.vanilla_ai & target.keep_mask) | value
        else:
            out[participant.level_cell] = value
    return out


def _stream(seed: int, salt: int) -> random.Random:
    return random.Random((seed << _SALT_SHIFT) ^ salt)


def _roll_stat(rng: random.Random, mode: int, low: int, high: int, sphere: int) -> int:
    if low >= high:
        return low
    if mode == STAT_RANDOM:
        return rng.randint(low, high)
    center = low + (high - low) * sphere / _MAX_SPHERE
    value = round(center + rng.choice(PROGRESSIVE_NOISE))
    return max(low, min(high, value))


def assign_levels(seed: int, mode: int, lo: int, hi: int) -> dict[int, int]:
    return _assign_stat(seed, LEVEL_TARGET, mode, lo, hi)


def assign_partners(seed: int, borgs_mode: int, ace_mode: int = SPECIAL_VANILLA) -> dict[int, int]:
    if borgs_mode == PARTNER_VANILLA and ace_mode == SPECIAL_VANILLA:
        return {}
    ace_map = _ace_permutation(seed, ace_mode)
    rng = _stream(seed, _SALT_PARTNER)
    out: dict[int, int] = {}
    for commander in sorted(PARTNER_FORCES):
        final_ace = ace_map.get(commander, SIGNATURE_BORGS[commander])
        for entries in PARTNER_FORCES[commander]:
            addrs = [slot.cell for slot in entries]
            vanilla = [slot.borg for slot in entries]
            with_ace = vanilla[-1] == SIGNATURE_BORGS[commander]
            regular = vanilla[:-1] if with_ace else vanilla
            final = _partner_regulars(rng, borgs_mode, regular) + ([final_ace] if with_ace else [])
            out.update(_list_writes(addrs, vanilla, final))
    return out


def _ace_permutation(seed: int, ace_mode: int) -> dict[int, int]:
    rng = _stream(seed, _SALT_ACE)
    if ace_mode == SPECIAL_SHUFFLE:
        commanders = sorted(ACE_ADDRS)
        aces = [SIGNATURE_BORGS[c] for c in commanders]
        rng.shuffle(aces)
        return dict(zip(commanders, aces, strict=True))
    if ace_mode == SPECIAL_RANDOM:
        return {c: rng.choice(_CANDIDATES) for c in sorted(ACE_ADDRS)}
    return {c: SIGNATURE_BORGS[c] for c in SIGNATURE_BORGS}


def _partner_regulars(rng: random.Random, borgs_mode: int, regular: list[int]) -> list[int]:
    if borgs_mode == PARTNER_RANDOM:
        return [rng.choice(_CANDIDATES) for _ in regular]
    if borgs_mode == PARTNER_BALANCED:
        if not regular:
            return []
        return _fill_budget(rng, sum(_spawn_cost(b) for b in regular), len(regular))
    return list(regular)


def _fill_budget(rng: random.Random, target: int, slots: int) -> list[int]:
    result: list[int] = []
    remaining = target
    for filled in range(slots):
        quota = remaining / (slots - filled)
        pool = [
            b
            for b in _CANDIDATES
            if quota * PARTNER_BUDGET_PICK_MIN_FACTOR <= COSTS[b] <= quota * PARTNER_BUDGET_PICK_MAX_FACTOR
        ]
        if pool:
            chosen = rng.choice(pool)
        else:
            chosen = min(_CANDIDATES, key=lambda b: abs(COSTS[b] - quota))
        result.append(chosen)
        remaining -= COSTS[chosen]
        if remaining < PARTNER_BUDGET_EXHAUSTED_BELOW and filled + 1 < slots:
            break
    return result


def _spawn_cost(borg_id: int) -> int:
    if borg_id in COSTS:
        return COSTS[borg_id]
    return SPAWN_COSTS.get(borg_id, 0)


def _list_writes(addrs: list[int], vanilla: list[int], final: list[int]) -> dict[int, int]:
    out: dict[int, int] = {}
    for index, addr in enumerate(addrs):
        if index < len(final):
            if final[index] != vanilla[index]:
                out[addr] = final[index]
        elif index == len(final):
            out[addr] = NO_ID
    return out


def chapter_costs(
    assignments: Mapping[int, int | None],
    inserts: Mapping[int, tuple[Escort, ...]] | None = None,
) -> dict[int, int]:
    extra = escort_costs(inserts) if inserts else {}
    costs: dict[int, int] = {}
    for chapter, spawns in SPAWNS.items():
        total = 0
        for spawn in spawns:
            final = assignments.get(spawn.cell, spawn.borg)
            if final is not None:
                total += _spawn_cost(final)
        costs[chapter] = total + extra.get(chapter, 0)
    return costs


def escort_costs(inserts: Mapping[int, tuple[Escort, ...]]) -> dict[int, int]:
    out: dict[int, int] = {}
    for cell, escorts in inserts.items():
        chapter = _CELL_CHAPTER[cell]
        out[chapter] = out.get(chapter, 0) + sum(_spawn_cost(e.borg) for e in escorts)
    return out


def pack_can_fuse(plan: EnemyPlan, cell: int) -> bool:
    return plan.packs.get(cell) in MACHINE_PACKS and not (
        plan.flag_writes.get(cell + FLAGS_OFF, SPAWN_FLAGS[cell]) & NO_BURST_BIT
    )


def plan_enemies(seed: int, mode: int, ace_mode: int = SPECIAL_VANILLA, boss_mode: int = SPECIAL_VANILLA) -> EnemyPlan:
    plan = EnemyPlan(assignments=dict(_assign_enemies(seed, mode, ace_mode, boss_mode)))
    if mode == MODE_VANILLA:
        return plan
    rng_boss = _stream(seed, _SALT_BOSS)
    rng_escort = _stream(seed, _SALT_ESCORT)
    cells = sorted(BOSS_ADDRS) + sorted(PACK_LEADER_CELLS)
    ids = _boss_ids(rng_boss, boss_mode, cells)
    if ids is not None:
        for cell in cells:
            plan.assignments.pop(cell, None)
        for cell, new_id in zip(cells, ids, strict=True):
            _place_boss(plan, rng_escort, mode, cell, new_id)
    _relocate_pairs(plan)
    return plan


def _assign_enemies(
    seed: int, mode: int, ace_mode: int = SPECIAL_VANILLA, boss_mode: int = SPECIAL_VANILLA
) -> dict[int, int]:
    out = _generic_pass(seed, mode)
    if mode == MODE_VANILLA:
        return out
    out.update(_ace_writes(seed, ace_mode))
    out.update(_boss_writes(seed, boss_mode))
    return out


def _generic_pass(seed: int, mode: int) -> dict[int, int]:
    rng = random.Random(seed)
    out: dict[int, int] = {}
    for chapter in sorted(SPAWNS):
        randomized = chapter not in PROTECTED_CHAPTERS and mode != MODE_VANILLA
        for spawn in SPAWNS[chapter]:
            if spawn.borg is None:
                out[spawn.cell] = _pinned_random_spawn(rng, spawn.choices, mode, randomized)
            elif randomized and _in_generic_pass(spawn.cell, spawn.borg):
                new_id = _mode_pick(rng, mode, SPAWN_COSTS.get(spawn.borg, 0), None)
                if new_id is not None:
                    out[spawn.cell] = new_id
    return out


def _pinned_random_spawn(rng: random.Random, options: Sequence[int], mode: int, randomized: bool) -> int:
    choice = rng.choice(options)
    if not randomized:
        return choice
    new_id = _mode_pick(rng, mode, SPAWN_COSTS.get(choice, 0), None)
    return choice if new_id is None else new_id


def _mode_pick(rng: random.Random, mode: int, base_cost: int, fallback: int | None) -> int | None:
    if mode == MODE_CHAOS:
        return rng.choice(_CANDIDATES)
    new_id = _balanced_pick(rng, base_cost)
    return fallback if new_id is None else new_id


def _balanced_pick(rng: random.Random, base_cost: int) -> int | None:
    low = max(MIN_BALANCED_COST, base_cost // BALANCED_COST_FACTOR)
    high = base_cost * BALANCED_COST_FACTOR
    pool = [b for b in _CANDIDATES if low <= COSTS[b] <= high]
    if not pool:
        return None
    return rng.choice(pool)


def _in_generic_pass(addr: int, borg_id: int) -> bool:
    return addr not in _SPECIAL_CELLS and (borg_id in BORGS or borg_id in ALT_FORMS)


def _ace_writes(seed: int, ace_mode: int) -> dict[int, int]:
    out: dict[int, int] = {}
    for commander, new_id in _ace_permutation(seed, ace_mode).items():
        if new_id != SIGNATURE_BORGS[commander] and commander in ACE_ADDRS:
            for addr in ACE_ADDRS[commander]:
                out[addr] = new_id
    return out


def _boss_writes(seed: int, boss_mode: int) -> dict[int, int]:
    rng_boss = _stream(seed, _SALT_BOSS)
    out: dict[int, int] = {}
    if boss_mode == BOSS_VANILLA:
        return out
    pool = BOSS_IDS if boss_mode == BOSS_ROSTER else _CANDIDATES
    for addr in sorted(BOSS_ADDRS):
        new_id = rng_boss.choice(pool)
        if new_id != BOSS_ADDRS[addr]:
            out[addr] = new_id
    return out


def _boss_ids(rng_boss: random.Random, boss_mode: int, cells: list[int]) -> list[int] | None:
    if boss_mode == BOSS_VANILLA:
        return None
    singles = BOSS_IDS if boss_mode == BOSS_ROSTER else _CANDIDATES
    return [rng_boss.choice(singles + PACK_KINDS if cell in _PACK_ELIGIBLE else singles) for cell in cells]


def _in_queue(queue: Queue, cell: int) -> bool:
    return queue.pointer <= cell < queue.pointer + queue.records * QUEUE_RECORD


_PACK_ELIGIBLE: frozenset[int] = frozenset(PACK_LEADER_CELLS) | frozenset(
    cell for cell in BOSS_ADDRS if _in_queue(QUEUE2[_CELL_CHAPTER[cell]], cell)
)


def _place_boss(plan: EnemyPlan, rng_escort: random.Random, mode: int, cell: int, new_id: int) -> None:
    escort_cells = PACK_ESCORT_CELLS.get(cell, ())
    if new_id in PACK_KINDS:
        free_cells = _place_pack(plan, cell, new_id, escort_cells)
    else:
        free_cells = _place_single_boss(plan, cell, new_id, escort_cells)
    _randomize_free_escorts(plan, rng_escort, mode, free_cells)


def _place_pack(plan: EnemyPlan, cell: int, kind: int, escort_cells: tuple[int, ...]) -> tuple[int, ...]:
    alone = kind in MACHINE_PACKS and pair_alone_at(cell)
    leader, escorts = pack_escorts(kind)
    plan.packs[cell] = kind
    _assign_cell(plan, cell, leader)
    plan.flag_writes[cell + FLAGS_OFF] = burst_flags(cell, alone)
    for escort_cell, escort in zip(escort_cells, escorts, strict=False):
        _assign_cell(plan, escort_cell, escort.borg)
        plan.flag_writes[escort_cell + FLAGS_OFF] = burst_flags(escort_cell, alone)
    leftover = escorts[len(escort_cells) :]
    if leftover:
        plan.inserts[cell] = leftover
    free_cells = escort_cells[len(escorts) :]
    if kind in MACHINE_PACKS and PACK_LEADER_CELLS.get(cell) == PACK_DARK_KNIGHT:
        for escort_cell in free_cells:
            plan.removes.add(escort_cell)
            plan.assignments[escort_cell] = None
        return ()
    return free_cells


def pair_alone_at(cell: int) -> bool:
    wave = ISOLATED_WAVES.get(_CELL_CHAPTER[cell])
    return (wave is not None and wave.leader_cell == cell) or PACK_LEADER_CELLS.get(cell) == PACK_DARK_KNIGHT


def pack_escorts(kind: int) -> tuple[int, tuple[Escort, ...]]:
    if kind == PACK_DARK_KNIGHT:
        return DARK_KNIGHT, tuple(
            Escort(escort.borg, escort.cap, None, escort.offset) for escort in DARK_KNIGHT_ESCORTS
        )
    if kind in MACHINE_PACKS:
        leader, escort = MACHINE_PACK_PAIRS[kind]
        return leader, (Escort(escort, MACHINE_ESCORT_CAP, None, _MACHINE_INSERT_DPOS),)
    raise ValueError(kind)


def _assign_cell(plan: EnemyPlan, cell: int, borg_id: int) -> None:
    if borg_id != _VANILLA_ID.get(cell):
        plan.assignments[cell] = borg_id


def burst_flags(cell: int, alone: bool) -> int:
    base = SPAWN_FLAGS[cell] & ~NO_BURST_BIT
    return base if alone else base | NO_BURST_BIT


def _place_single_boss(plan: EnemyPlan, cell: int, borg_id: int, escort_cells: tuple[int, ...]) -> tuple[int, ...]:
    _assign_cell(plan, cell, borg_id)
    if PACK_LEADER_CELLS.get(cell) in MACHINE_PACKS:
        plan.flag_writes[cell + FLAGS_OFF] = burst_flags(cell, False)
        for escort_cell in escort_cells:
            plan.flag_writes[escort_cell + FLAGS_OFF] = burst_flags(escort_cell, False)
    return escort_cells


def _randomize_free_escorts(plan: EnemyPlan, rng_escort: random.Random, mode: int, cells: tuple[int, ...]) -> None:
    for escort_cell in cells:
        pick = _generic_pick(rng_escort, mode, escort_cell)
        if pick is not None and pick != _VANILLA_ID.get(escort_cell):
            plan.assignments[escort_cell] = pick


def _generic_pick(rng: random.Random, mode: int, addr: int) -> int | None:
    if mode == MODE_CHAOS:
        return rng.choice(_CANDIDATES)
    vanilla = _VANILLA_ID.get(addr)
    cost = SPAWN_COSTS.get(vanilla, 0) if vanilla is not None else 0
    return _balanced_pick(rng, cost)


def _relocate_pairs(plan: EnemyPlan) -> None:
    for chapter in sorted(ISOLATED_WAVES):
        if chapter in PROTECTED_CHAPTERS:
            continue
        leader_cell, partner_cell = ISOLATED_WAVES[chapter]
        if leader_cell in _SPECIAL_CELLS or partner_cell in _SPECIAL_CELLS:
            continue
        cells = [spawn.cell for spawn in SPAWNS[chapter] if spawn.cell not in _SPECIAL_CELLS]
        final = {addr: plan.assignments.get(addr, _VANILLA_ID.get(addr)) for addr in cells}
        for first_id, second_id in FUSION_PAIRS:
            cells_first = [c for c in cells if final[c] == first_id]
            cells_second = [c for c in cells if final[c] == second_id]
            if not cells_first or not cells_second:
                continue
            _swap(final, leader_cell, cells_first[0])
            second_now = next(c for c in cells if final[c] == second_id)
            _swap(final, partner_cell, second_now)
            for cell in (leader_cell, partner_cell, cells_first[0], second_now):
                if final[cell] is not None:
                    plan.assignments[cell] = final[cell]
            plan.flag_writes[leader_cell + FLAGS_OFF] = burst_flags(leader_cell, True)
            plan.flag_writes[partner_cell + FLAGS_OFF] = burst_flags(partner_cell, True)
            plan.pairs[chapter] = (first_id, second_id)
            break


def _swap(final: dict[int, int | None], cell_a: int, cell_b: int) -> None:
    if cell_a != cell_b:
        final[cell_a], final[cell_b] = final[cell_b], final[cell_a]


def cell_chapter(cell: int) -> int:
    return _CELL_CHAPTER[cell]


def vanilla_id(cell: int) -> int | None:
    return _VANILLA_ID.get(cell)


def pack_members(plan: EnemyPlan, cell: int) -> list[int]:
    ids = [plan.assignments.get(cell, _VANILLA_ID.get(cell))]
    kind = plan.packs[cell]
    n_escorts = len(DARK_KNIGHT_ESCORTS) if kind == PACK_DARK_KNIGHT else MACHINE_PAIR_ESCORTS
    ids.extend(
        plan.assignments.get(escort_cell, _VANILLA_ID.get(escort_cell))
        for escort_cell in PACK_ESCORT_CELLS.get(cell, ())[:n_escorts]
    )
    ids.extend(e.borg for e in plan.inserts.get(cell, ()))
    return [i for i in ids if i is not None]


def inserted_borgs(inserts: Mapping[int, tuple[Escort, ...]]) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for cell, escorts in inserts.items():
        out.setdefault(_CELL_CHAPTER[cell], []).extend(e.borg for e in escorts)
    return out
