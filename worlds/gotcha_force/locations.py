from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING, Final

from BaseClasses import Location

from .data.achievements import NO_CASUALTIES_CHAPTERS, THEME_CHAPTERS
from .data.borgs import BORGS
from .data.chapters import CHAPTERS
from .data.companions import COMPANIONS
from .data.gacha import GACHA_REGISTERS
from .data.rewards import REWARDS, Reward
from .data.zones import ZONES
from .game import GAME_NAME
from .logic import achievements
from .logic.achievements import (
    ChapterSpec,
    CommanderChapterSpec,
    CommanderSpec,
    Spec,
    TribeSpec,
)
from .logic.progression import PARTNER_CHOICE
from .regions import STORY_MAP_REGION

if TYPE_CHECKING:
    from .world import GotchaForceWorld

LOCATION_ID_BASE: Final = 690_000_000

CHECKS_PER_CHAPTER: Final = 3

CHECK_CHAPTERS: Final = tuple(sorted(CHAPTERS))

CHECK_NAME_PREFIX: Final = "Chapter "
GACHA_PREFIX: Final = "Gacha - "
ACHIEVEMENT_PREFIX: Final = "Achievement - "

IDS_PER_CHAPTER: Final = 10
REWARD_ID_OFFSET: Final = 5000
GACHA_ID_OFFSET: Final = 30_000
GACHA_IDS_PER_BORG: Final = 8

SINGLE_PIECE: Final = 1

GACHA_WHOLE_OFFSET: Final = 7

ACHIEVEMENT_ID_BASE: Final = LOCATION_ID_BASE + 100_000
RIVAL_STYLE_ID_OFFSET: Final = 100
ACE_DUEL_ID_OFFSET: Final = 200
RIVAL_STYLE_ALL_ID_OFFSET: Final = 1000
COMMANDER_ID_SLOTS: Final = 16
TRIBE_FORCE_ID_OFFSET: Final = 5000
THEME_ID_OFFSET: Final = 6000
ALLY_FINISHER_ID_OFFSET: Final = 7000
NO_CASUALTIES_ID_OFFSET: Final = 8000

ACHIEVEMENT_NAME_FORMATS: Final = {
    achievements.TYPE_PARTNER_STYLE: "Partner Style: {commander}",
    achievements.TYPE_COMMANDER_STYLE: "Rival Style: {commander}",
    achievements.TYPE_COMMANDER_STYLE_ALL: "Rival Style: {commander} - Chapter {chapter}",
    achievements.TYPE_TRIBE_FORCE: "Tribe Force: {tribe}",
    achievements.TYPE_THEME: "Theme: Chapter {chapter} ({theme})",
    achievements.TYPE_ALLY_FINISHER: "Ally Finisher: Chapter {chapter}",
    achievements.TYPE_NO_CASUALTIES: "No Casualties: Chapter {chapter}",
    achievements.TYPE_ACE_DUEL: "Ace Duel: {commander}",
}


class GotchaForceLocation(Location):
    game = GAME_NAME

def _build_table() -> dict[str, int]:
    ids: dict[str, int] = {}
    for chapter in CHECK_CHAPTERS:
        for check_number in range(1, CHECKS_PER_CHAPTER + 1):
            ids[check_location_name(chapter, check_number)] = (
                LOCATION_ID_BASE + chapter * IDS_PER_CHAPTER + check_number - 1
            )
    for ordinal, reward in enumerate(REWARDS):
        ids[reward.name] = LOCATION_ID_BASE + REWARD_ID_OFFSET + ordinal
    for borg_id, register in GACHA_REGISTERS.items():
        for piece in range(1, register.pieces + 1):
            ids[gacha_location_name(borg_id, piece)] = (
                LOCATION_ID_BASE + GACHA_ID_OFFSET + borg_id * GACHA_IDS_PER_BORG + piece - 1
            )
        if register.pieces > SINGLE_PIECE:
            ids[gacha_whole_location_name(borg_id)] = (
                LOCATION_ID_BASE + GACHA_ID_OFFSET + borg_id * GACHA_IDS_PER_BORG + GACHA_WHOLE_OFFSET
            )
    ids.update(_achievement_ids())
    return ids

def check_location_name(chapter: int, check_number: int) -> str:
    return f"{CHECK_NAME_PREFIX}{chapter:03d} - Check {check_number}"

def gacha_location_name(borg_id: int, piece: int) -> str:
    total = GACHA_REGISTERS[borg_id].pieces
    name = BORGS[borg_id].name
    if total <= SINGLE_PIECE:
        return GACHA_PREFIX + name
    return f"{GACHA_PREFIX}{name} {piece}/{total}"


def gacha_whole_location_name(borg_id: int) -> str:
    return GACHA_PREFIX + BORGS[borg_id].name

def _achievement_ids() -> dict[str, int]:
    ids: dict[str, int] = {}
    for commander in COMPANIONS:
        ids[achievement_location_name(CommanderSpec(achievements.TYPE_PARTNER_STYLE, commander))] = (
            ACHIEVEMENT_ID_BASE + commander
        )
        ids[achievement_location_name(CommanderSpec(achievements.TYPE_COMMANDER_STYLE, commander))] = (
            ACHIEVEMENT_ID_BASE + RIVAL_STYLE_ID_OFFSET + commander
        )
        ids[achievement_location_name(CommanderSpec(achievements.TYPE_ACE_DUEL, commander))] = (
            ACHIEVEMENT_ID_BASE + ACE_DUEL_ID_OFFSET + commander
        )
    for chapter in CHECK_CHAPTERS:
        for commander in CHAPTERS[chapter].antagonists:
            spec = CommanderChapterSpec(achievements.TYPE_COMMANDER_STYLE_ALL, commander, chapter)
            ids[achievement_location_name(spec)] = (
                ACHIEVEMENT_ID_BASE + RIVAL_STYLE_ALL_ID_OFFSET + chapter * COMMANDER_ID_SLOTS + commander
            )
    for ordinal, tribe in enumerate(achievements.TRIBE_ORDER):
        ids[achievement_location_name(TribeSpec(achievements.TYPE_TRIBE_FORCE, tribe))] = (
            ACHIEVEMENT_ID_BASE + TRIBE_FORCE_ID_OFFSET + ordinal
        )
    for chapter in THEME_CHAPTERS:
        ids[achievement_location_name(ChapterSpec(achievements.TYPE_THEME, chapter))] = (
            ACHIEVEMENT_ID_BASE + THEME_ID_OFFSET + chapter
        )
    for chapter in _ally_finisher_chapters():
        ids[achievement_location_name(ChapterSpec(achievements.TYPE_ALLY_FINISHER, chapter))] = (
            ACHIEVEMENT_ID_BASE + ALLY_FINISHER_ID_OFFSET + chapter
        )
    for chapter in NO_CASUALTIES_CHAPTERS:
        ids[achievement_location_name(ChapterSpec(achievements.TYPE_NO_CASUALTIES, chapter))] = (
            ACHIEVEMENT_ID_BASE + NO_CASUALTIES_ID_OFFSET + chapter
        )
    return ids


def achievement_location_name(spec: Spec) -> str:
    spec = achievements.as_spec(spec)
    if spec.kind not in ACHIEVEMENT_NAME_FORMATS:
        raise ValueError(spec)
    return ACHIEVEMENT_PREFIX + ACHIEVEMENT_NAME_FORMATS[spec.kind].format(**_spec_labels(spec))


def _spec_labels(spec: Spec) -> dict[str, str]:
    labels: dict[str, str] = {}
    fields = spec._asdict()
    if "commander" in fields:
        labels["commander"] = COMPANIONS[fields["commander"]]
    if "chapter" in fields:
        labels["chapter"] = f"{fields['chapter']:03d}"
        labels["theme"] = THEME_CHAPTERS.get(fields["chapter"], "")
    if "tribe" in fields:
        labels["tribe"] = fields["tribe"]
    return labels


def _ally_finisher_chapters() -> list[int]:
    return [chapter for chapter in CHECK_CHAPTERS
            if CHAPTERS[chapter].partner_mode == PARTNER_CHOICE]


LOCATION_NAME_TO_ID = _build_table()

def _zone_groups() -> dict[str, set[str]]:
    return {
        f"Zone - {zone}": {
            check_location_name(chapter, check_number)
            for chapter in CHECK_CHAPTERS if CHAPTERS[chapter].tile == tile
            for check_number in range(1, CHECKS_PER_CHAPTER + 1)
        }
        for tile, zone in ZONES.items()
    }


LOCATION_NAME_GROUPS: dict[str, set[str]] = {
    "Vanilla Rewards": {reward.name for reward in REWARDS},
    "Gacha": {n for n in LOCATION_NAME_TO_ID if n.startswith(GACHA_PREFIX)},
    "Achievements": set(_achievement_ids()),
    **_zone_groups(),
}

def create_all_locations(world: GotchaForceWorld) -> None:
    region = world.get_region(STORY_MAP_REGION)
    for name in _seed_location_names(world):
        region.locations.append(GotchaForceLocation(
            world.player, name, LOCATION_NAME_TO_ID[name], region
        ))

def _seed_location_names(world: GotchaForceWorld) -> list[str]:
    names: list[str] = []
    names.extend(
        check_location_name(chapter, check_number)
        for chapter in world.chapters_in_pool
        for check_number in range(1, world.options.mission_checks.value + 1)
    )
    names += [reward.name for reward in pool_rewards(world)]
    whole = gacha_only_one_per_borg(world)
    for borg_id in sorted(world.gacha_chapters):
        names += gacha_locations_for(borg_id, whole)
    names += [achievement_location_name(spec) for spec in world.achievement_plan.specs]
    return names

def starting_spots(world: GotchaForceWorld,
                   open_chapters: Collection[int]) -> int:
    opened = set(open_chapters)
    spots = len(opened) * world.options.mission_checks.value
    spots += sum(1 for reward in pool_rewards(world)
                 if opened.intersection(reward.triggers))
    whole = gacha_only_one_per_borg(world)
    for borg_id, chapters in world.gacha_chapters.items():
        if opened & chapters:
            spots += len(gacha_locations_for(borg_id, whole))
    return spots


def pool_rewards(world: GotchaForceWorld) -> list[Reward]:
    chapters = world.chapters_in_pool
    return [reward._replace(triggers=tuple(c for c in reward.triggers if c in chapters))
            for reward in REWARDS
            if any(c in chapters for c in reward.triggers)]


def gacha_only_one_per_borg(world: GotchaForceWorld) -> bool:
    opt = world.options.gacha_checks
    return opt == opt.option_one_per_borg


def gacha_locations_for(borg_id: int, whole: bool) -> list[str]:
    if whole:
        return [gacha_whole_location_name(borg_id)]
    return [gacha_location_name(borg_id, piece)
            for piece in range(1, GACHA_REGISTERS[borg_id].pieces + 1)]


