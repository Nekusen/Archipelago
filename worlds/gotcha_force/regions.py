from __future__ import annotations

from typing import TYPE_CHECKING, Final

from BaseClasses import Region

if TYPE_CHECKING:
    from .world import GotchaForceWorld

MENU_REGION: Final = "Menu"
STORY_MAP_REGION: Final = "Story Map"
GOAL_ARENA_REGION: Final = "Goal Arena"
MAP_ACCESS_ENTRANCE: Final = "Map Access"
GOAL_GATE_ENTRANCE: Final = "Goal Gate"


def create_and_connect_regions(world: GotchaForceWorld) -> None:
    player, multiworld = world.player, world.multiworld
    menu = Region(MENU_REGION, player, multiworld)
    story = Region(STORY_MAP_REGION, player, multiworld)
    goal = Region(GOAL_ARENA_REGION, player, multiworld)

    menu.connect(story, MAP_ACCESS_ENTRANCE)
    menu.connect(goal, GOAL_GATE_ENTRANCE)

    multiworld.regions.extend([menu, story, goal])
