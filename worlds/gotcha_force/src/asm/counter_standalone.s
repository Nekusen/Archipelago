# counter_standalone: counter_create without the list check or the displaced call, for debugging
# hook : none; call it from a memory tool or a debugger
# load : COUNTER_STANDALONE
# uses : r14, r15 (saved and restored); volatile registers (it calls game routines)
    stwu 1, -0x20(1)
    mflr 0
    stw 0, 0x24(1)
    stw 14, 0x8(1)
    stw 15, 0xc(1)
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
    lwz 14, 0x8(1)
    lwz 15, 0xc(1)
    lwz 0, 0x24(1)
    mtlr 0
    addi 1, 1, 0x20
    blr
