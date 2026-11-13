# icon_tint: colors the icon of a map row from its chapter's AP_FLAGS: green done, dark out of logic
# hook : ICON_TINT_HOOK_CURSOR and ICON_TINT_HOOK_BLINK, by bl    (was: bl SPRITE_SET_COLOR)
# load : ICON_TINT_ROUTINE
# in   : r3 = the object, r4 = the color the game chose (SELECTED_ROW_COLOR under the cursor)
# uses : r0, r4-r8, r11, r12, cr0 (volatile across the original bl)
# note : ends in a tail jump to SPRITE_SET_COLOR, whose blr returns to the game; tinting here,
#        not in counter_update, avoids a one-frame flicker on every cursor move
    lbz 5, $OBJ_DESCRIPTOR_INDEX(3)
    andi. 5, 5, $DESC_INDEX_GLYPH_MASK
    cmpwi 5, $GLYPH_INDEX_ICON
    bne apply
    lwz 5, $PROGRESS_PTR_SDA(13)
    lbz 6, $OBJ_DESCRIPTOR_INDEX(3)
    srawi 6, 6, $DESC_INDEX_ROW_SHIFT
    addi 6, 6, -1                    # row
    lwz 7, $OFF_CUR_ZONE(5)
    slwi 7, 7, $MAP_TILE_SLOTS_SHIFT
    lwz 8, $OFF_PANEL_SCROLL(5)
    add 7, 7, 8
    add 7, 7, 6
    add 7, 7, 5
    lbz 7, $OFF_MAP_LISTS(7)         # chapter
    lis 8, hi(AP_FLAGS)
    addi 8, 8, lo(AP_FLAGS)
    lbzx 8, 8, 7
    li 11, $TINT_PAIR_VANILLA
    andi. 0, 8, $AP_FLAG_DONE
    beq not_done
    li 11, $TINT_PAIR_DONE
    b pick
not_done:
    andi. 0, 8, $AP_FLAG_OUT_OF_LOGIC
    beq pick
    li 11, $TINT_PAIR_OUT_OF_LOGIC
pick:
    lis 6, hi(AP_TINTS)
    addi 6, 6, lo(AP_TINTS)
    add 6, 6, 11
    cmpwi 4, $SELECTED_ROW_COLOR
    beq selected
    lwz 4, $TINT_UNSELECTED_OFF(6)
    b apply
selected:
    lwz 4, 0(6)
apply:
    jump SPRITE_SET_COLOR
