# counter_update: places, frames and shows or hides one digit of its map row's X/Y (from AP_TABLE)
# hook : none; the game calls it every frame, as the update callback counter_create sets
# load : COUNTER_UPDATE
# in   : r3 = the digit object
# uses : r24-r31 (saved and restored); volatile registers (it calls game routines)
# regs : r31 obj, r25 bar, r24 icon, r26 row, r27 k (glyph in the row), r28 X, r29 Y, r30 frame,
#        r11 value being split, r12 digit position, r9 DECIMAL_BASE, r10 HUNDRED
# note : nothing is cached in the object, so the digits follow the bar while it slides in;
#        the "/" glyph (GLYPH_SLASH) also tints the row's icon from AP_FLAGS
    stwu 1, -0x40(1)
    mflr 0
    stw 0, 0x44(1)
    stmw 24, 0x20(1)
    mr 31, 3
    lbz 0, $OBJ_PATCH_INITIALIZED(31)
    cmpwi 0, 0
    bne update
    li 0, 1
    stb 0, $OBJ_PATCH_INITIALIZED(31)
    li 0, $OBJ_INIT_BYTE_VALUE
    stb 0, $OBJ_INIT_BYTE(31)
    lis 4, hi(OBJ_DRAW_FN)
    addi 4, 4, lo(OBJ_DRAW_FN)
    stw 4, $OBJ_DRAW_FN_OFF(31)
    mr 3, 31
    li 4, 0
    li 5, 1
    call OBJ_RENDER_REGISTER
    li 0, 0
    sth 0, $OBJ_ROTATION_X(31)
    sth 0, $OBJ_ROTATION_Y(31)
    sth 0, $OBJ_ROTATION_Z(31)
    lbz 0, $OBJ_DESCRIPTOR_INDEX(31)
    andi. 0, 0, $DESC_INDEX_GLYPH_MASK
    cmpwi 0, $SLASH_GLYPH_INDEX
    bne no_rotation
    li 0, $SLASH_ROTATION
    sth 0, $OBJ_ROTATION_Z(31)
no_rotation:
    mr 3, 31
    li 4, 0
    call UI_OBJECT_BIND_ANIM
update:
    lbz 0, $OBJ_DESCRIPTOR_INDEX(31)
    srawi 26, 0, $DESC_INDEX_ROW_SHIFT
    addi 26, 26, -1                  # row
    andi. 27, 0, $DESC_INDEX_GLYPH_MASK
    addi 27, 27, -$GLYPH_INDEX_FIRST # k, the glyph in the row
    lbz 5, $OBJ_DESCRIPTOR_INDEX(31)
    andi. 5, 5, $DESC_INDEX_ROW_MASK # index of the row's bar
    addi 7, 5, 1                     # index of the row's icon
    lis 3, hi(UI_LIST_HEAD)
    lwz 3, lo(UI_LIST_HEAD)(3)
    li 25, 0
    li 24, 0
    li 4, $UI_LIST_WALK_LIMIT
find_row:
    cmplwi 3, 0
    beq found
    addic. 4, 4, -1
    beq found
    lbz 0, $OBJ_TYPE(3)
    cmpwi 0, $OBJ_TYPE_PANEL_ROW
    bne next_object
    lbz 0, $OBJ_DESCRIPTOR_INDEX(3)
    cmpw 0, 5
    bne check_icon
    mr 25, 3
    cmplwi 24, 0
    bne found
    b next_object
check_icon:
    cmpw 0, 7
    bne next_object
    mr 24, 3
    cmplwi 25, 0
    bne found
next_object:
    lwz 3, $OBJ_NEXT(3)
    b find_row
found:
    cmplwi 25, 0
    beq hide
    lbz 0, $OBJ_VISIBILITY(25)       # bar hidden: digits hidden
    cmpwi 0, 0
    beq hide
    lwz 3, $PROGRESS_PTR_SDA(13)
    lwz 4, $OFF_CUR_ZONE(3)
    slwi 4, 4, $MAP_TILE_SLOTS_SHIFT
    add 4, 4, 3
    lwz 0, $OFF_PANEL_SCROLL(3)
    add 4, 4, 0
    add 4, 4, 26
    lbz 8, $OFF_MAP_LISTS(4)         # chapter = map list[zone * slots + scroll + row]
    slwi 5, 8, $AP_TABLE_ENTRY_SHIFT
    lis 6, hi(AP_TABLE)
    addi 6, 6, lo(AP_TABLE)
    add 6, 6, 5
    lbz 28, $AP_TABLE_DONE_OFF(6)    # X
    lbz 29, $AP_TABLE_TOTAL_OFF(6)   # Y
    cmpwi 27, $GLYPH_SLASH
    bne tint_done
    cmplwi 24, 0
    beq tint_done
    lis 6, hi(AP_FLAGS)
    addi 6, 6, lo(AP_FLAGS)
    lbzx 7, 6, 8
    li 11, $TINT_PAIR_VANILLA
    andi. 0, 7, $AP_FLAG_DONE
    beq tint_not_done
    li 11, $TINT_PAIR_DONE
    b tint_pick
tint_not_done:
    andi. 0, 7, $AP_FLAG_OUT_OF_LOGIC
    beq tint_pick
    li 11, $TINT_PAIR_OUT_OF_LOGIC
tint_pick:
    lis 6, hi(AP_TINTS)
    addi 6, 6, lo(AP_TINTS)
    add 6, 6, 11
    lwz 3, $PROGRESS_PTR_SDA(13)
    lwz 0, $OFF_PANEL_SELECTED_ROW(3)
    cmpw 26, 0
    beq tint_selected
    lwz 4, $TINT_UNSELECTED_OFF(6)
    b tint_apply
tint_selected:
    lwz 4, 0(6)
tint_apply:
    mr 3, 24
    call SPRITE_SET_COLOR
tint_done:
    cmpwi 29, 0
    beq hide                         # Y == 0: nothing to count on this row
    li 9, $DECIMAL_BASE
    li 10, $HUNDRED
    cmpwi 27, $GLYPH_SLASH
    beq slash
    blt side_x
    mr 11, 29                        # k 4..6: digits of Y
    addi 12, 27, -$GLYPH_Y_FIRST     # digit position
    b digit
side_x:
    mr 11, 28                        # k 0..2: digits of X
    mr 12, 27
digit:
    cmpwi 12, 0
    beq hundreds
    cmpwi 12, 1
    beq tens
    divwu 4, 11, 9
    mulli 0, 4, $DECIMAL_BASE
    subf 30, 0, 11                   # units
    b place
hundreds:
    cmpw 11, 10
    blt hide                         # leading zero: hidden
    divwu 30, 11, 10
    b place
tens:
    cmpw 11, 9
    blt hide
    divwu 4, 11, 9
    divwu 5, 4, 9
    mulli 0, 5, $DECIMAL_BASE
    subf 30, 0, 4
    b place
slash:
    li 30, $GLYPH_ONE
place:
    cmpw 28, 29
    bne slot
    addi 30, 30, $YELLOW_GLYPH_OFFSET  # X == Y: yellow glyphs
slot:
    cmpwi 27, $GLYPH_SLASH
    blt slot_x
    beq slot_zero
    cmpwi 27, $GLYPH_Y_FIRST
    beq slot_one
    cmpwi 27, $GLYPH_Y_TENS
    beq slot_k5
    li 7, 1                          # k 6: units of Y, right after its wider digits
    cmpw 29, 9
    blt slot_done
    addi 7, 7, 1
    cmpw 29, 10
    blt slot_done
    addi 7, 7, 1
    b slot_done
slot_k5:
    li 7, 1
    cmpw 29, 10
    blt slot_done
    li 7, 2
    b slot_done
slot_one:
    li 7, 1
    b slot_done
slot_zero:
    li 7, 0
    b slot_done
slot_x:
    addi 7, 27, -$GLYPH_SLASH        # k 0..2: slots -3..-1, right-aligned against the "/"
slot_done:
    addi 7, 7, $SLOT_INDEX_BIAS
    slwi 7, 7, $FLOAT_SHIFT
    lis 4, hi(SLOT_FLOATS)
    addi 4, 4, lo(SLOT_FLOATS)
    lfsx 2, 4, 7
    lis 4, hi(DIGIT_SPACING)
    lfs 3, lo(DIGIT_SPACING)(4)
    fmuls 2, 2, 3
    lfs 0, $OBJ_POS_X(25)            # bar x
    lis 4, hi(X_OFFSET)
    lfs 3, lo(X_OFFSET)(4)
    fadds 0, 0, 3
    fadds 0, 0, 2
    stfs 0, $OBJ_POS_X(31)
    lfs 0, $OBJ_POS_Y(25)            # bar y
    lis 4, hi(Y_OFFSET)
    lfs 3, lo(Y_OFFSET)(4)
    fadds 0, 0, 3
    stfs 0, $OBJ_POS_Y(31)
    li 0, $OBJ_VISIBLE
    stb 0, $OBJ_VISIBILITY(31)
    lis 4, hi(FRAME_FLOATS)
    addi 4, 4, lo(FRAME_FLOATS)
    slwi 0, 30, $FLOAT_SHIFT
    lfsx 1, 4, 0                     # f1 = frame as float
    mr 3, 31
    li 4, 0
    call UI_OBJECT_SPRITE_SET_FRAME
    lis 4, hi(DIGIT_SCALE)
    lfs 0, lo(DIGIT_SCALE)(4)
    stfs 0, $OBJ_SCALE_X(31)
    stfs 0, $OBJ_SCALE_Y(31)
    stfs 0, $OBJ_SCALE_Z(31)
    b done
hide:
    li 0, $OBJ_HIDDEN
    stb 0, $OBJ_VISIBILITY(31)
done:
    lmw 24, 0x20(1)
    lwz 0, 0x44(1)
    mtlr 0
    addi 1, 1, 0x40
    blr
