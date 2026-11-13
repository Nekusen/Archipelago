# story_borg: the borg deployed without the Gotcha Box comes from AP_STORY_BORG, not a fixed G Red
# hook : STORY_BORG_HOOK, by bl    (was: li r26, 0x615)
# load : STORY_BORG_ROUTINE
# uses : r26 only
# note : no CR field is touched: the game's `beq` after the hook still tests its own compare
    lis 26, hi(AP_STORY_BORG)
    lhz 26, lo(AP_STORY_BORG)(26)
    blr
