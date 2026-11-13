"""Generated from the game's data tables. Do not edit by hand."""

from typing import NamedTuple


class Reward(NamedTuple):
    key: str
    name: str                   # the location name
    triggers: tuple[int, ...]   # the first of these chapters to be completed fires it


REWARDS: tuple[Reward, ...] = (
    Reward("companion_1", "Reward: Recruit Kakeru", (2,)),
    Reward("companion_2", "Reward: Recruit Mana", (3,)),
    Reward("companion_3", "Reward: Recruit Sho", (136,)),
    Reward("companion_4", "Reward: Recruit Tetsuya", (70,)),
    Reward("companion_5", "Reward: Recruit Kotaro", (71,)),
    Reward("companion_6", "Reward: Recruit Tsutomu", (5,)),
    Reward("companion_7", "Reward: Recruit Nekobe", (56,)),
    Reward("companion_8", "Reward: Recruit Kitsune", (92,)),
    Reward("companion_9", "Reward: Recruit Met", (131,)),
    Reward("companion_10", "Reward: Recruit Tama", (124,)),
    Reward("companion_11", "Reward: Recruit Usagi", (5,)),
    Reward("companion_12", "Reward: Recruit Yuji", (133,)),
    Reward("gf_cap_600", "Reward: GF Energy Cap 600", (1,)),
    Reward("gf_cap_1000", "Reward: GF Energy Cap 1000", (9,)),
    Reward("gf_cap_1500", "Reward: GF Energy Cap 1500", (18, 19)),
    Reward("gf_cap_2000", "Reward: GF Energy Cap 2000", (34,)),
    Reward("gf_cap_2500", "Reward: GF Energy Cap 2500", (115,)),
    Reward("gf_cap_3500", "Reward: GF Energy Cap 3500", (21,)),
    Reward("upgrade_1", "Reward: Commander Upgrade Level 1", (9, 83)),
    Reward("upgrade_2", "Reward: Commander Upgrade Level 2", (18, 19, 84)),
    Reward("upgrade_3", "Reward: Commander Upgrade Level 3", (24, 134)),
    Reward("upgrade_5", "Reward: Commander Upgrade Level 5", (21,)),
    Reward("crystal_1", "Reward: Death Crystal 1", (88, 119)),
    Reward("crystal_2", "Reward: Death Crystal 2", (120,)),
    Reward("crystal_3", "Reward: Death Crystal 3", (117,)),
    Reward("map_expanded", "Reward: Expanded Map", (1,)),
    Reward("map_full", "Reward: Full Map", (2,)),
    Reward("scenario_11", "Reward: Death Base Arena", (24, 134)),
    Reward("scenario_13", "Reward: Special Arena", (34,)),
    Reward("gotcha_box", "Reward: Gotcha Box", (9,)),
    Reward("neo_g_red", "Reward: Neo G Red", (24,)),
    Reward("death_gate", "Reward: Death Gate", (158,)),
)
