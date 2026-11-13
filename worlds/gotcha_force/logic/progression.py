from __future__ import annotations

import random
from collections.abc import Iterable

from ..data.chapters import (
    CHAPTERS,
    COSMIC_DRAGON_CHAPTER,
    DARK_KNIGHT_CHAPTERS,
    GALACTIC_EMPEROR_CHAPTERS,
    TUTORIAL_CHAPTER,
    VARIANT_PAIRS,
)
from ..data.companions import COMPANIONS
from ..data.main_missions import MAIN_CHAPTERS

GOAL_COSMIC_DRAGON = 0
GOAL_GALACTIC_EMPEROR = 1
GOAL_DARK_KNIGHT = 2
GOAL_CUSTOM = 3
GOAL_RANDOM_MISSION = 4

FIXED_GOAL_CHAPTERS: dict[int, tuple[int, ...]] = {
    GOAL_COSMIC_DRAGON: (COSMIC_DRAGON_CHAPTER,),
    GOAL_GALACTIC_EMPEROR: GALACTIC_EMPEROR_CHAPTERS,
    GOAL_DARK_KNIGHT: DARK_KNIGHT_CHAPTERS,
}

RANDOM_GOAL_FLOOR = GOAL_DARK_KNIGHT

POOL_ALL = 0
POOL_MAIN = 1
POOL_CUSTOM = 2

PARTNER_NONE = 0
PARTNER_FIXED = (1, 2)
PARTNER_CHOICE = 3
ALL_COMPANIONS: frozenset[int] = frozenset(COMPANIONS)


def random_goal_candidates() -> list[int]:
    floor = _goal_sphere(FIXED_GOAL_CHAPTERS[RANDOM_GOAL_FLOOR])
    return sorted(c for c in CHAPTERS if c != TUTORIAL_CHAPTER and CHAPTERS[c].sphere >= floor)


def _goal_sphere(goal_chapters: Iterable[int]) -> int:
    caps = []
    for chapter in goal_chapters:
        spheres = [CHAPTERS[chapter].sphere]
        for pair in VARIANT_PAIRS:
            if chapter in pair:
                spheres = [CHAPTERS[m].sphere for m in pair]
        caps.append(min(spheres))
    return min(caps)


def pick_variants(
    goal_chapters: Iterable[int], mission_pool: int, rng: random.Random, plando: Iterable[int] = ()
) -> tuple[int, ...]:
    goal_set = set(goal_chapters)
    cut = _chapters_past_goal(goal_set)
    base = MAIN_CHAPTERS if mission_pool == POOL_MAIN else frozenset(CHAPTERS)
    wanted = set(plando)
    picks: list[int] = []
    for pair in VARIANT_PAIRS:
        in_goal = [m for m in pair if m in goal_set]
        if in_goal:
            picks.extend(in_goal)
            continue
        alive = [m for m in pair if m not in cut and m in base]
        plandoed = [m for m in alive if m in wanted]
        candidates = plandoed if plandoed else alive
        if candidates:
            picks.append(rng.choice(candidates))
    return tuple(picks)


def _chapters_past_goal(goal_chapters: Iterable[int]) -> set[int]:
    goal_set = set(goal_chapters)
    cap = _goal_sphere(goal_set)
    return {c for c, ch in CHAPTERS.items() if ch.sphere > cap and c not in goal_set}


def resolve_custom_chapters(
    goal_chapters: Iterable[int], variant_picks: Iterable[int], plando: Iterable[int], count: int, rng: random.Random
) -> tuple[int, ...]:
    candidates = [c for c in chapter_pool(goal_chapters, POOL_ALL, variant_picks) if c != TUTORIAL_CHAPTER]
    chosen = {c for c in plando if c in candidates}
    remainder = [c for c in candidates if c not in chosen]
    missing = max(0, count - len(chosen))
    filler = rng.sample(remainder, min(missing, len(remainder)))
    return tuple(sorted(chosen | set(filler) | {TUTORIAL_CHAPTER}))


def chapter_pool(
    goal_chapters: Iterable[int],
    mission_pool: int = POOL_ALL,
    variant_picks: Iterable[int] = (),
    custom_chapters: Iterable[int] = (),
) -> list[int]:
    goal_set = set(goal_chapters)
    cut = _chapters_past_goal(goal_set)
    if mission_pool == POOL_CUSTOM:
        base = (set(custom_chapters) | {TUTORIAL_CHAPTER}) & CHAPTERS.keys()
    elif mission_pool == POOL_MAIN:
        base = MAIN_CHAPTERS
    else:
        base = CHAPTERS.keys()
    chosen = set(variant_picks) | goal_set
    discarded = {m for pair in VARIANT_PAIRS if chosen & set(pair) for m in pair if m not in chosen}
    return sorted(c for c in base if c not in cut and c not in goal_set and c not in discarded)


def keys_needed_by_chapter(pool: Iterable[int], story_keys: int) -> dict[int, int]:
    order = sorted(pool, key=lambda c: (CHAPTERS[c].sphere, c))
    total = len(order)
    if not total:
        return {}
    segments = story_keys + 1
    return {c: pos * segments // total for pos, c in enumerate(order)}


def partner_requirement_met(chapter: int, unlocked: Iterable[int]) -> bool:
    if CHAPTERS[chapter].partner_mode == PARTNER_NONE:
        return True
    return bool(eligible_partners(chapter) & frozenset(unlocked))


def eligible_partners(chapter: int) -> frozenset[int]:
    header = CHAPTERS[chapter]
    if header.partner_mode == PARTNER_NONE:
        return frozenset()
    if header.partner_mode == PARTNER_CHOICE:
        return ALL_COMPANIONS - frozenset(header.antagonists)
    return frozenset({header.partner})


def partner_label(chapter: int) -> str:
    header = CHAPTERS[chapter]
    if header.partner_mode == PARTNER_NONE:
        return "Kou alone"
    if header.partner_mode == PARTNER_CHOICE:
        excluded = ", ".join(COMPANIONS[a] for a in header.antagonists)
        exclusion = f" (not {excluded})" if excluded else ""
        return f"any partner{exclusion}"
    return f"partner {COMPANIONS[header.partner]}"
