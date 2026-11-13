# gacha_credit: with AP_GACHA_CREDIT set, in story mode, kills by the partner also fill the gacha meter
# hook : GACHA_CREDIT_HOOK, by bl    (was: lbz r0, 0x3e6(r28), the gate of the meter in kill_handler)
# load : GACHA_CREDIT_ROUTINE
# in   : r28 = the killer entity
# uses : r0, r12, cr0 (the caller's `extsb.` redefines cr0)
# note : r0 = 0 passes the gate; a killer of the enemy team returns its team number and is rejected
#        as in vanilla; disarmed or outside story mode, it is just the displaced load
    lis 12, hi(AP_GACHA_CREDIT)
    lbz 12, lo(AP_GACHA_CREDIT)(12)
    cmpwi 12, 0
    beq vanilla
    lwz 12, $BATTLE_CFG_SDA(13)
    lbz 12, $BATTLE_CFG_MODE(12)
    cmpwi 12, $BATTLE_MODE_STORY
    bne vanilla
    lbz 0, $ENT_CPU_FLAG(28)
    cmpwi 0, 0
    beqlr                            # human killer: passes
    lbz 0, $ENT_TEAM(28)             # team of the killer: 0 = the player's side
    blr
vanilla:
    lbz 0, $ENT_CPU_FLAG(28)
    blr
