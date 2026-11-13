from __future__ import annotations

from dataclasses import dataclass

from Options import (
    Choice,
    DefaultOnToggle,
    OptionError,
    OptionGroup,
    OptionSet,
    PerGameCommonOptions,
    Range,
    Toggle,
)

from .data.chapters import CHAPTERS, TUTORIAL_CHAPTER, VARIANT_PAIRS
from .logic.achievements import (
    ALL_TYPES,
    TRIBE_ORDER,
    TYPE_COMMANDER_STYLE,
    TYPE_COMMANDER_STYLE_ALL,
    TYPE_PARTNER_STYLE,
    TYPE_THEME,
    TYPE_TRIBE_FORCE,
)
from .logic.enemies import (
    BOSS_FULL_RANDOM,
    BOSS_ROSTER,
    BOSS_VANILLA,
    MODE_BALANCED,
    MODE_CHAOS,
    MODE_VANILLA,
    PARTNER_BALANCED,
    PARTNER_RANDOM,
    PARTNER_VANILLA,
    SPECIAL_RANDOM,
    SPECIAL_SHUFFLE,
    SPECIAL_VANILLA,
    STAT_PROGRESSIVE,
    STAT_RANDOM,
    STAT_VANILLA,
)
from .logic.progression import (
    GOAL_COSMIC_DRAGON,
    GOAL_CUSTOM,
    GOAL_DARK_KNIGHT,
    GOAL_GALACTIC_EMPEROR,
    GOAL_RANDOM_MISSION,
    POOL_ALL,
    POOL_CUSTOM,
    POOL_MAIN,
)

UNLIMITED_RATIO = float("inf")


class Goal(Choice):
    """The mission whose victory wins your game. It unlocks by
    collecting Death Crystals (see Death Crystals Required), and any
    mission that comes later than it in the story is left out of the
    game entirely.

    - cosmic_dragon: the Cosmic Dragon at the Sky Fortress.
    - galactic_emperor: the final battle. Almost the whole story is in
      play.
    - dark_knight: the Dark Knight showdown (a shorter game).
    - custom: pick any mission yourself with Goal Mission.
    - random_mission: a mission picked by the seed, at least as deep
      into the story as the Dark Knight (revealed by the client and
      the spoiler).

    A few story battles exist in two exclusive versions (you only ever
    see one in a normal playthrough); each seed picks one version and
    only that one exists — including for the goal itself.
    """

    display_name = "Goal"
    option_cosmic_dragon = GOAL_COSMIC_DRAGON
    option_galactic_emperor = GOAL_GALACTIC_EMPEROR
    option_dark_knight = GOAL_DARK_KNIGHT
    option_custom = GOAL_CUSTOM
    option_random_mission = GOAL_RANDOM_MISSION
    default = option_cosmic_dragon


class GoalMission(Range):
    """Only with goal: custom — the internal chapter id of the mission
    whose victory is your goal (the ids are listed in the client's
    Tracker tab and in the spoiler as "NNN - Title"). Ignored with any
    other goal. A very early mission leaves few missions in the seed
    and generation may fail: raise Mission Checks or keep Gacha
    Locations on to make room."""

    display_name = "Goal Mission"
    range_start = 0
    range_end = max(CHAPTERS)
    default = 0


class MissionPool(Choice):
    """Which missions are in your seed (besides the goal).

    - all: every story mission.
    - main: only the main-story experience — the missions a normal
      playthrough goes through, without the optional side missions
      that stretch the game (about 60, following the story's main
      path).
    - random_custom: a set of missions picked by the seed. Choose how
      many with Custom Mission Count, and pin missions you want in
      with Custom Missions; the rest are drawn at random.

    Missions that come later than the goal are always left out.
    """

    display_name = "Mission Pool"
    option_all = POOL_ALL
    option_main = POOL_MAIN
    option_random_custom = POOL_CUSTOM
    default = option_all


class CustomMissionCount(Range):
    """Only with mission_pool: random_custom — how many missions are
    in your seed. The first mission is always included on top of this
    number, and the goal mission is never part of it. If you ask for
    more missions than exist before your goal, you simply get all of
    them. Very low counts can fail to generate: raise Mission Checks
    or keep Gacha Locations on to make room."""

    display_name = "Custom Mission Count"
    range_start = 10
    range_end = len(CHAPTERS) - 1
    default = 40


class CustomMissions(OptionSet):
    """Only with mission_pool: random_custom — mission ids that are
    guaranteed to be in your seed, for example ["18", "45", "120"]
    (the ids are listed in the client's Tracker tab and in the spoiler
    as "NNN - Title"). If the list is shorter than Custom Mission
    Count, the rest are drawn at random; if it is longer, everything
    you listed is still included. Missions that cannot be in the seed
    (the goal, missions later than the goal in the story) are quietly
    skipped. For story battles that exist in two exclusive versions,
    listing one pins that version for the whole seed — never list
    both."""

    display_name = "Custom Missions"


class DeathCrystalsInPool(Range):
    """How many Death Crystal items are placed in the item pool. The
    crystals above Death Crystals Required are spares: when a small
    seed has no room for all of them, the spares are dropped (never
    the required ones) and the generator says so."""

    display_name = "Death Crystals in Pool"
    range_start = 1
    range_end = 50
    default = 20


class DeathCrystalsRequired(Range):
    """How many Death Crystals you need to unlock the goal mission.
    Must not be higher than the number of crystals in the pool."""

    display_name = "Death Crystals Required"
    range_start = 1
    range_end = 50
    default = 12


class StoryKeys(Range):
    """How many Progressive Story Keys are in the item pool. Your
    missions are sorted by story order and split into that many
    batches plus one: the first batch is open from the start, and each
    key opens the next batch. With 0, every mission is open from the
    beginning."""

    display_name = "Story Keys"
    range_start = 0
    range_end = 10
    default = 8


class GachaLocations(DefaultOnToggle):
    """Turns the Gotcha Borg gacha into Archipelago checks.

    - On: whenever the gacha pops after a battle, it sends a check
      instead of giving you the borg. Each borg you can meet as an
      enemy has its own checks (how many, see Gacha Checks), and every
      gacha only pops once. Borgs are added to the item pool so they
      reach you through the multiworld. The total number depends on
      which enemies appear in your seed. A small set of borgs is
      marked progression and guaranteed to show up early-ish, so you
      always have something to fight with; logic itself only gates
      missions by GF Energy.
    - Off: the gacha works like in the original game and hands out
      borgs directly. Borgs are not part of the item pool.
    """

    display_name = "Gacha Locations"


class GachaPartnerKills(DefaultOnToggle):
    """In the original game, an enemy only fills the gacha meter when
    YOU land the final blow — kills by your partner don't count, so
    borgs you clearly fought sometimes never show up in the gacha.

    - On (recommended): every defeated enemy on your side's scoreboard
      fills the gacha meter, no matter who landed the final blow.
    - Off: original behavior, only your own kills count.

    Battle-results statistics are not affected either way.
    """

    display_name = "Gacha Counts Partner Kills"


class GachaRate(Range):
    """How fast the gacha fills up. Higher values make it pop much more
    often; at high settings, beating a new enemy type usually pops its
    gacha in that same battle. 1 is the original game's speed (very
    slow, not recommended). Also works as a quality-of-life boost when
    Gacha Locations is off — in that case borgs you already own go back
    to the normal rate so you are not flooded with copies."""

    display_name = "Gacha Rate"
    range_start = 1
    range_end = 100
    default = 20


class GachaChecks(Choice):
    """How many checks the gacha gives for each borg (only matters when
    Gacha Locations is on).

    - per_fragment: one check for every piece a borg is made of, like
      the original game hands them out, so a borg of three pieces has
      to be beaten three times.
    - one_per_borg: a single check for each borg, no matter how many
      pieces it has. Every borg only has to be beaten once, and there
      are fewer gacha checks in total.

    This setting is independent of Borg Items: if you want complete
    borgs AND one check each, set Borg Items to whole and this to
    one_per_borg.
    """

    display_name = "Gacha Checks"
    option_per_fragment = 0
    option_one_per_borg = 1
    default = option_per_fragment


class Achievements(Toggle):
    """Adds achievement checks: extra objectives such as winning with a
    borg matching your partner's style, beating a commander while
    carrying a borg of their style, fielding a whole force of one
    tribe, or bringing a themed borg to a themed mission. Pick which
    kinds with Achievement Types. Every achievement is based on the
    original game's styles and themes, and the client's Tracker tab
    lists each objective."""

    display_name = "Achievement Locations"


class AchievementTypes(OptionSet):
    """Which achievement types are in play (only with Achievement
    Locations on). Types listed here are added as checks; the rest are
    left out.

    - partner_style: win any mission that puts a partner at your side
      while carrying a borg of that partner's style (one check per
      commander).
    - commander_style: win any one mission against each commander
      while carrying a borg of their style (one check per commander).
    - commander_style_all: the same, but every mission where that
      commander opposes you has its own check. Cannot be combined
      with commander_style.
    - tribe_force: win any mission with a force made of a single
      tribe, worth at least Tribe Force Minimum Cost (one check per
      tribe with enough borgs).
    - theme_missions: win a themed mission (dragons, bugs, heroes...)
      while carrying a borg of its theme.
    - ally_finisher: win a mission where your PARTNER lands the blow
      that ends the battle. A seeded 10% sample of the missions where
      you choose your partner gets a check each.
    - no_casualties: win a few handpicked missions without losing a
      single borg. These checks only appear when those missions keep
      their original enemies.
    - ace_duel: defeat each commander while carrying their own
      signature borg (Sasuke against Kakeru, Kei against Usagi...) —
      the original game's ace, even if this seed shuffles aces around.
    """

    display_name = "Achievement Types"
    valid_keys = ALL_TYPES
    default = frozenset(
        {
            TYPE_PARTNER_STYLE,
            TYPE_COMMANDER_STYLE,
            TYPE_TRIBE_FORCE,
            TYPE_THEME,
        }
    )


class TribeForceMinCost(Range):
    """Minimum total cost of the single-tribe force for tribe_force
    achievements. Tribes that cannot reach this cost in your seed do
    not get a check."""

    display_name = "Tribe Force Minimum Cost"
    range_start = 300
    range_end = 3500
    default = 1500


class TribeForceTribes(OptionSet):
    """Which tribes get a tribe_force achievement. Only matters when
    tribe_force is among the Achievement Types: the tribes listed here
    get a check each, the rest get none. A tribe that cannot reach
    Tribe Force Minimum Cost in your seed is skipped anyway. Names are
    the original game's tribes, in any capitalization."""

    display_name = "Tribe Force Tribes"
    valid_keys = frozenset(t.casefold() for t in TRIBE_ORDER)
    valid_keys_casefold = True
    default = tuple(t.casefold() for t in TRIBE_ORDER)


class MissionChecks(Range):
    """How many checks each story mission sends when you complete it."""

    display_name = "Checks per Mission"
    range_start = 1
    range_end = 3
    default = 1


class BorgItems(Choice):
    """How borgs appear in the item pool (only matters when Gacha
    Locations is on).

    - fragments: borgs arrive in pieces, like in the original game.
      Collect all the pieces of a borg to complete it.
    - whole: every borg item is a complete, ready-to-use borg.
    """

    display_name = "Borg Items"
    option_fragments = 0
    option_whole = 1
    default = option_fragments


class CommanderItems(Choice):
    """How the GF Commanders (your recruitable friends) appear in the
    item pool.

    Missions that put a partner at Kou's side need that partner: a
    mission with a fixed partner needs that commander, and a mission
    where you pick your partner needs at least one recruited commander
    who is not the rival of that mission. Missions Kou plays alone
    need nobody. A mission stays hidden on the map until you have a
    partner it accepts.

    In both modes one item recruits each commander.

    - global_upgrades: shared upgrade items raise the level of every
      commander at once, like in the original game.
    - individual: each commander has their own upgrade items, which
      raise only their level. Upgrades found before the commander wait
      and apply the moment the commander joins.
    """

    display_name = "Commander Items"
    option_global_upgrades = 0
    option_individual = 1
    default = option_global_upgrades


class AreaAccessItems(DefaultOnToggle):
    """Adds one Area Access item per map zone. Missions in a zone only
    show up once you have received its access item. The whole map is
    always visible, and you start with access to the zone (or zones)
    around your home."""

    display_name = "Area Access Items"


class GotchaBox(Choice):
    """How you get the Gotcha Box, which lets you choose the borgs you
    take into battle.

    - randomized: the Gotcha Box is an item in the multiworld. Until it
      arrives you fight with your starting borg alone.
    - unlocked: you have the Gotcha Box from the start, with its two
      borgs.
    """

    display_name = "Gotcha Box"
    option_randomized = 0
    option_unlocked = 1
    default = option_randomized


class GFLogicDifficulty(Choice):
    """How strong your GF Energy is expected to be before the game
    logic counts a mission as beatable. You can always try harder
    missions early at your own risk — this only affects where required
    items can be placed.

    - normal: comfortable fights, close to a regular playthrough.
    - hard: expects you to win against noticeably stronger enemy teams.
    - very_hard: expects wins against the toughest odds the original
      game ever asks for.
    - no_cap: GF Energy is ignored by the logic entirely.
    """

    display_name = "GF Energy Logic Difficulty"
    option_normal = 0
    option_hard = 1
    option_very_hard = 2
    option_no_cap = 3
    default = option_normal


class StartingBorg(Choice):
    """Which borg you start the game with.

    - vanilla: G Red, like in the original game.
    - random_borg: a random borg, G Red and Neo G Red included. Very
      weak ones are never picked, so you always have missions you can
      reasonably beat from the start.

    Starting with G Red or Neo G Red hands you the matching Progressive
    G Red items right away, and they leave the pool.
    """

    display_name = "Starting Borg"
    option_vanilla = 0
    option_random_borg = 1
    default = option_random_borg


class EnemyRandomization(Choice):
    """Shuffles which enemy borgs you fight. The same mission always
    has the same enemies within one seed, even if you retry it.

    - vanilla: the original enemy line-ups.
    - balanced: every enemy is swapped for one of similar strength, so
      the difficulty curve stays close to the original game.
    - chaos: any enemy can appear anywhere. Wild swings in difficulty.

    Story bosses and the final battles always keep their identity. The
    Galactic Emperor only ever appears in its own final battle.
    """

    display_name = "Enemy Randomization"
    option_vanilla = MODE_VANILLA
    option_balanced = MODE_BALANCED
    option_chaos = MODE_CHAOS
    default = option_balanced


class CommanderAceBorgs(Choice):
    """What happens to each rival commander's signature borg (for
    example Kakeru's Sasuke). Only used when Enemy Randomization is
    balanced or chaos.

    - vanilla: every commander keeps their signature borg even when
      the rest of their team is randomized.
    - shuffle: the signature borgs are swapped around between the
      commanders.
    - full_random: each commander gets a random borg as their
      signature.
    """

    display_name = "Commander Ace Borgs"
    option_vanilla = SPECIAL_VANILLA
    option_shuffle = SPECIAL_SHUFFLE
    option_full_random = SPECIAL_RANDOM
    default = option_vanilla


class BossBorgs(Choice):
    """What happens to the big boss enemies of the story: the Flame,
    Blizzard, Plasma and Cosmic Dragons, the Cyber Death Dragon, the
    Ultimate Cannon, the ICBM Tank, the Death Saucer, the Dark Knight's
    trio and the four pairs of Machine Borgs that merge in battle. Only
    used when Enemy Randomization is balanced or chaos.

    - vanilla: every boss keeps its identity.
    - random_boss: every boss slot gets one of those bosses drawn at
      random, so a seed can have several of one and none of another.
    - full_random: each boss slot gets a completely random enemy.

    Some bosses travel as a group: the Dark Knight always brings his
    Sapphire Knight and Ruby Knight, and each Machine pair comes
    together. Wherever they land, the whole group spawns together; a
    Machine pair can merge in battle only when it gets the field to
    itself, like in the story.

    The final battles of both goals are never changed.
    """

    display_name = "Boss Borgs"
    option_vanilla = BOSS_VANILLA
    option_random_boss = BOSS_ROSTER
    option_full_random = BOSS_FULL_RANDOM
    default = option_vanilla


class PartnerBorgs(Choice):
    """Shuffles the borgs your ally partner brings into battle.

    - vanilla: partners use their original teams.
    - balanced: partner teams are rebuilt with different borgs of
      similar overall strength.
    - full_random: partner teams are fully random. A higher partner
      level can end up with a weaker team — that is part of the fun.
    """

    display_name = "Partner Borgs"
    option_vanilla = PARTNER_VANILLA
    option_balanced = PARTNER_BALANCED
    option_full_random = PARTNER_RANDOM
    default = option_vanilla


class PartnerAceBorgs(Choice):
    """What happens to your partners' signature borgs (the special borg
    each friend always brings).

    - vanilla: every partner keeps their own signature borg.
    - shuffle: the signature borgs are swapped around between partners.
    - full_random: each partner gets a random borg as their signature.
    """

    display_name = "Partner Ace Borgs"
    option_vanilla = SPECIAL_VANILLA
    option_shuffle = SPECIAL_SHUFFLE
    option_full_random = SPECIAL_RANDOM
    default = option_vanilla


class EnemyAI(Choice):
    """How sharp the enemy borgs' reflexes are. Higher AI values make
    enemies attack, dodge and switch targets more often, without
    changing which enemies appear.

    - vanilla: the original game's AI.
    - progressive: random, but later missions tend to get sharper
      enemies.
    - random_ai: fully random between the minimum and maximum below.
    """

    display_name = "Enemy AI Randomization"
    option_vanilla = STAT_VANILLA
    option_progressive = STAT_PROGRESSIVE
    option_random_ai = STAT_RANDOM
    default = option_vanilla


class EnemyAIMinimum(Range):
    """Lowest possible enemy AI (0 = barely reacts). Only used with
    progressive or random AI. If minimum and maximum are equal, every
    enemy uses exactly that value."""

    display_name = "Enemy AI Minimum"
    range_start = 0
    range_end = 15
    default = 0


class EnemyAIMaximum(Range):
    """Highest possible enemy AI. 12 is the strongest the original game
    uses; 13 to 15 go beyond it, up to superhuman reflexes."""

    display_name = "Enemy AI Maximum"
    range_start = 0
    range_end = 15
    default = 12


class EnemyLevels(Choice):
    """Randomizes the level of enemy borgs. Higher-level enemies hit
    harder and take more hits. The rewards you get are the same either
    way: the level of an enemy does not change what it drops.

    - vanilla: the original levels.
    - progressive: random, but later missions tend to have higher
      levels.
    - random_levels: fully random between the minimum and maximum.
    """

    display_name = "Enemy Level Randomization"
    option_vanilla = STAT_VANILLA
    option_progressive = STAT_PROGRESSIVE
    option_random_levels = STAT_RANDOM
    default = option_vanilla


class EnemyLevelMinimum(Range):
    """Lowest possible enemy level. Only used with progressive or
    random levels. If minimum and maximum are equal, every enemy uses
    exactly that level."""

    display_name = "Enemy Level Minimum"
    range_start = 0
    range_end = 10
    default = 0


class EnemyLevelMaximum(Range):
    """Highest possible enemy level. 8 is the highest the original
    game uses; 9 and 10 go beyond it."""

    display_name = "Enemy Level Maximum"
    range_start = 0
    range_end = 10
    default = 8


@dataclass
class GotchaForceOptions(PerGameCommonOptions):
    goal: Goal
    goal_mission: GoalMission
    mission_pool: MissionPool
    custom_mission_count: CustomMissionCount
    custom_missions: CustomMissions
    story_keys: StoryKeys
    death_crystals_in_pool: DeathCrystalsInPool
    death_crystals_required: DeathCrystalsRequired
    gacha_locations: GachaLocations
    gacha_partner_kills: GachaPartnerKills
    gacha_rate: GachaRate
    gacha_checks: GachaChecks
    achievements: Achievements
    achievement_types: AchievementTypes
    tribe_force_min_cost: TribeForceMinCost
    tribe_force_tribes: TribeForceTribes
    mission_checks: MissionChecks
    borg_items: BorgItems
    commander_items: CommanderItems
    area_access_items: AreaAccessItems
    gotcha_box: GotchaBox
    gf_logic_difficulty: GFLogicDifficulty
    starting_borg: StartingBorg
    enemy_randomization: EnemyRandomization
    commander_ace_borgs: CommanderAceBorgs
    boss_borgs: BossBorgs
    partner_borgs: PartnerBorgs
    partner_ace_borgs: PartnerAceBorgs
    enemy_ai: EnemyAI
    enemy_ai_minimum: EnemyAIMinimum
    enemy_ai_maximum: EnemyAIMaximum
    enemy_levels: EnemyLevels
    enemy_level_minimum: EnemyLevelMinimum
    enemy_level_maximum: EnemyLevelMaximum


OPTION_GROUPS = [
    OptionGroup(
        "Goal",
        [
            Goal,
            GoalMission,
            MissionPool,
            CustomMissionCount,
            CustomMissions,
            StoryKeys,
            DeathCrystalsInPool,
            DeathCrystalsRequired,
        ],
    ),
    OptionGroup(
        "Pool",
        [
            GachaLocations,
            GachaRate,
            GachaChecks,
            Achievements,
            AchievementTypes,
            TribeForceMinCost,
            TribeForceTribes,
            MissionChecks,
            BorgItems,
            CommanderItems,
            AreaAccessItems,
            GotchaBox,
        ],
    ),
    OptionGroup(
        "Difficulty",
        [
            GFLogicDifficulty,
            StartingBorg,
            EnemyRandomization,
            CommanderAceBorgs,
            BossBorgs,
            PartnerBorgs,
            PartnerAceBorgs,
            EnemyAI,
            EnemyAIMinimum,
            EnemyAIMaximum,
            EnemyLevels,
            EnemyLevelMinimum,
            EnemyLevelMaximum,
        ],
    ),
]

DIFFICULTY_RATIOS = {
    GFLogicDifficulty.option_normal: 1.89,
    GFLogicDifficulty.option_hard: 3.0,
    GFLogicDifficulty.option_very_hard: 4.79,
    GFLogicDifficulty.option_no_cap: UNLIMITED_RATIO,
}

STARTING_BORG_MIN_COST = {
    GFLogicDifficulty.option_normal: 140,
    GFLogicDifficulty.option_hard: 90,
    GFLogicDifficulty.option_very_hard: 60,
    GFLogicDifficulty.option_no_cap: 60,
}


def validate_options(options: GotchaForceOptions, player_name: str) -> None:
    _validate_crystals(options, player_name)
    _validate_goal_mission(options, player_name)
    _validate_custom_missions(options, player_name)
    _validate_achievement_types(options, player_name)
    _validate_range("enemy_ai", options.enemy_ai_minimum, options.enemy_ai_maximum, player_name)
    _validate_range("enemy_level", options.enemy_level_minimum, options.enemy_level_maximum, player_name)


def _validate_crystals(options: GotchaForceOptions, player_name: str) -> None:
    pool = options.death_crystals_in_pool.value
    required = options.death_crystals_required.value
    if required > pool:
        raise OptionError(
            f"{player_name}: death_crystals_required ({required}) cannot exceed death_crystals_in_pool ({pool})"
        )


def _validate_goal_mission(options: GotchaForceOptions, player_name: str) -> None:
    if options.goal != options.goal.option_custom:
        return
    chapter = options.goal_mission.value
    if chapter not in CHAPTERS:
        raise OptionError(
            f"{player_name}: goal_mission ({chapter}) is not a valid "
            f"chapter (see the ids in the spoiler or the tracker)"
        )
    if chapter == TUTORIAL_CHAPTER:
        raise OptionError(f"{player_name}: goal_mission cannot be the tutorial (chapter {TUTORIAL_CHAPTER})")


def _validate_custom_missions(options: GotchaForceOptions, player_name: str) -> None:
    if options.mission_pool != options.mission_pool.option_random_custom:
        return
    ids = _custom_mission_ids(options, player_name)
    for pair in VARIANT_PAIRS:
        if set(pair) <= ids:
            raise OptionError(
                f"{player_name}: custom_missions asks for both "
                f"exclusive versions {pair[0]} and {pair[1]} "
                f"of the same battle; only one exists in each "
                f"seed - keep only the one you want"
            )


def _custom_mission_ids(options: GotchaForceOptions, player_name: str) -> set[int]:
    ids: set[int] = set()
    for entry in options.custom_missions.value:
        try:
            chapter = int(entry)
        except (TypeError, ValueError):
            raise OptionError(
                f"{player_name}: custom_missions contains "
                f"'{entry}', which is not a chapter id (use "
                f'numbers, e.g. ["18", "45"])'
            ) from None
        if chapter not in CHAPTERS:
            raise OptionError(
                f"{player_name}: custom_missions ({chapter}) is not a "
                f"valid chapter (see the ids in the spoiler or the "
                f"tracker)"
            )
        ids.add(chapter)
    return ids


def _validate_achievement_types(options: GotchaForceOptions, player_name: str) -> None:
    if not options.achievements:
        return
    types = set(options.achievement_types.value)
    if {TYPE_COMMANDER_STYLE, TYPE_COMMANDER_STYLE_ALL} <= types:
        raise OptionError(
            f"{player_name}: commander_style and commander_style_all "
            f"are mutually exclusive in achievement_types; keep only one"
        )


def _validate_range(name: str, minimum: Range, maximum: Range, player_name: str) -> None:
    if minimum.value > maximum.value:
        raise OptionError(
            f"{player_name}: {name}_minimum ({minimum.value}) cannot exceed {name}_maximum ({maximum.value})"
        )
