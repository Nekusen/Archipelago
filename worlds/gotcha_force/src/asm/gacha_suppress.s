# gacha_suppress: while AP_GACHA_SUPPRESS is set the game grants no reward (the animation still plays)
# hook : GACHA_GRANT_HOOK, by b    (was: stwu r1, -0x20(r1), first instruction of reward_grant_dispatch)
# load : GACHA_SUPPRESS_ROUTINE
# uses : r12, cr0 (dead at function entry)
# note : LR is still the caller's, so `li 3, 0` + `blr` returns "no reward" straight to it;
#        disarmed, it runs the displaced instruction and jumps to GACHA_GRANT_RESUME
    lis 12, hi(AP_GACHA_SUPPRESS)
    lbz 12, lo(AP_GACHA_SUPPRESS)(12)
    cmpwi 12, 0
    beq vanilla
    li 3, 0
    blr
vanilla:
    stwu 1, -0x20(1)                 # the displaced instruction
    jump GACHA_GRANT_RESUME
