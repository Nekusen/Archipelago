# counter_create: creates the 35 digit objects of the map's X/Y counters, then makes the displaced call
# hook : MARKER_HOOK_ADDR, by b    (was: bl MARKER_HOOK_DISPLACED_CALL)
# load : COUNTER_CREATE
# uses : r14, r15 (saved and restored); volatile registers (it calls game routines)
# note : a digit already in the ui list means the screen is re-entered: then only the displaced call;
#        it returns with `jump MARKER_HOOK_RETURN`
    stwu 1, -0x20(1)
    mflr 0
    stw 0, 0x24(1)
    stw 14, 0x8(1)
    stw 15, 0xc(1)
    lis 3, hi(UI_LIST_HEAD)
    lwz 3, lo(UI_LIST_HEAD)(3)
    lis 14, hi(COUNTER_UPDATE)
    addi 14, 14, lo(COUNTER_UPDATE)
    li 15, $UI_LIST_WALK_LIMIT
find_existing:
    cmplwi 3, 0
    beq create
    addic. 15, 15, -1
    beq create
    lwz 0, $OBJ_UPDATE_CALLBACK(3)
    cmpw 0, 14
    beq dispatch_only                # one of ours already exists
    lwz 3, $OBJ_NEXT(3)
    b find_existing
create:
    lis 14, hi(DIGIT_DESCRIPTORS)
    addi 14, 14, lo(DIGIT_DESCRIPTORS)
    li 15, 0
next_glyph:
    li 3, $OBJ_TYPE_HUD
    mr 4, 14
    call UI_OBJECT_CREATE
    cmplwi 3, 0
    beq skip_glyph
    lis 4, hi(COUNTER_UPDATE)
    addi 4, 4, lo(COUNTER_UPDATE)
    stw 4, $OBJ_UPDATE_CALLBACK(3)
    lis 4, hi(OBJ_DRAW_CALLBACK)
    addi 4, 4, lo(OBJ_DRAW_CALLBACK)
    stw 4, $OBJ_DRAW_CALLBACK_OFF(3)
skip_glyph:
    addi 14, 14, $DESCRIPTOR_SIZE
    addi 15, 15, 1
    cmpwi 15, $DIGIT_COUNT
    blt next_glyph
dispatch_only:
    call MARKER_HOOK_DISPLACED_CALL  # creates the map controller, last in the list as in vanilla
    lwz 14, 0x8(1)
    lwz 15, 0xc(1)
    lwz 0, 0x24(1)
    mtlr 0
    addi 1, 1, 0x20
    jump MARKER_HOOK_RETURN
