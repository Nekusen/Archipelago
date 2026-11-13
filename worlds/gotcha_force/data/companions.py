"""Generated from the game's data tables. Do not edit by hand."""

# index -> name of the 13 companions, matched to their index
# through the in-game mission titles; renaming one only changes
# the label, not the mechanics.
COMPANIONS: dict[int, str] = {
    1: "Kakeru",
    2: "Mana",
    3: "Sho",
    4: "Tetsuya",
    5: "Kotaro",
    6: "Tsutomu",
    7: "Nekobe",
    8: "Kitsune",
    9: "Met",
    10: "Tama",
    11: "Usagi",
    12: "Yuji",
    13: "Orochi",
}

# index -> usable chapters that recruit it in vanilla
# (13, Orochi, belongs to route 2+: an item with no location)
COMPANION_TRIGGERS: dict[int, tuple[int, ...]] = {
    1: (2,),
    2: (3,),
    3: (136,),
    4: (70,),
    5: (71,),
    6: (5,),
    7: (56,),
    8: (92,),
    9: (131,),
    10: (124,),
    11: (5,),
    12: (133,),
}

# the levels a commander's upgrades reach; the game never gives Kotaro
# levels 3 and 4, and in global mode he runs one step behind the rest
KOTARO = 5
UPGRADE_LADDER = (1, 2, 3, 4, 5)
KOTARO_UPGRADE_LADDER = (1, 2, 5)
KOTARO_GLOBAL_LEVELS = (0, 1, 2, 2, 5)
