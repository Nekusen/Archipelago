"""Named addresses of the DOL patch: game routines it calls, hook sites, the layout of the new section,
the game structures its routines read and the values baked into its tables. Every integer here is a
symbol of the assembler sources (``$NAME``, ``hi(NAME)``, ``lo(NAME)``)."""

from typing import Final

# Game routines and globals
UI_OBJECT_CREATE: Final = 0x801A7538            # (type, descriptor) -> ui object, or 0
UI_OBJECT_BIND_ANIM: Final = 0x801A7688         # (obj, 0): binds the animation named in the descriptor
UI_OBJECT_SPRITE_SET_FRAME: Final = 0x801A76FC  # (obj, 0, f1 = frame): selects the glyph of sprite 0
SPRITE_SET_COLOR: Final = 0x801A76C0            # (obj, rgba): tints sprite 0 of the object
OBJ_RENDER_REGISTER: Final = 0x80089100         # (obj, 0, 1): registers the object with the renderer
OBJ_DRAW_CALLBACK: Final = 0x801E29DC           # obj+0x10C of the HUD objects: draws unconditionally
OBJ_DRAW_FN: Final = 0x80047AA4                 # obj+0x100 as the game's own init routines set it
UI_LIST_HEADS: Final = 0x803C706C               # array of ui object list heads
UI_LIST_INDEX: Final = 0x39                     # the list that holds the map panel rows and the HUD
POINTER_SIZE: Final = 4
UI_LIST_HEAD: Final = UI_LIST_HEADS + UI_LIST_INDEX * POINTER_SIZE
UI_LIST_WALK_LIMIT: Final = 0x400               # objects a list walk gives up after
PROGRESS_PTR_SDA: Final = -0x524C               # r13-relative offset of the pointer to the progress block
BATTLE_CFG_SDA: Final = -0x7C70                 # r13-relative offset of the pointer to the battle config

# Ui object fields (offsets from the object)
OBJ_NEXT: Final = 0x08                          # next object in the list
OBJ_UPDATE_CALLBACK: Final = 0x0C               # per-frame callback
OBJ_TYPE: Final = 0x10                          # object type
OBJ_DESCRIPTOR_INDEX: Final = 0x11              # the descriptor's index byte
OBJ_PATCH_INITIALIZED: Final = 0x18             # set once by counter_update on its first frame
OBJ_SCALE_X: Final = 0x58                       # 3 x f32
OBJ_SCALE_Y: Final = 0x5C
OBJ_SCALE_Z: Final = 0x60
OBJ_POS_X: Final = 0x64                         # 2 x f32
OBJ_POS_Y: Final = 0x68
OBJ_ROTATION_X: Final = 0x70                    # 3 x s16, 0x8000 = 180 degrees
OBJ_ROTATION_Y: Final = 0x72
OBJ_ROTATION_Z: Final = 0x74
OBJ_VISIBILITY: Final = 0x82                    # 0 hidden; the game's HUD objects use 4
OBJ_INIT_BYTE: Final = 0x84                     # set to OBJ_INIT_BYTE_VALUE by the game's own HUD init routines
OBJ_DRAW_FN_OFF: Final = 0x100
OBJ_DRAW_CALLBACK_OFF: Final = 0x10C
OBJ_INIT_BYTE_VALUE: Final = 0x1F
OBJ_VISIBLE: Final = 4
OBJ_HIDDEN: Final = 0

# Progress block fields the routines read (offsets from the progress block)
OFF_CUR_ZONE: Final = 0x118                     # u32: tile selected on the map
OFF_MAP_LISTS: Final = 0x174                    # 13 x 0x40 u8: chapter of mission i
MAP_TILE_SLOTS_SHIFT: Final = 6                 # 0x40 entries per tile
OFF_PANEL_SCROLL: Final = 0x9D0                 # u32: first row shown by the map panel
OFF_PANEL_SELECTED_ROW: Final = 0x9D4           # u32: row under the cursor

# Battle config and entity fields the gacha credit routine reads
BATTLE_CFG_MODE: Final = 0x32                   # u8: 0 = story mode
BATTLE_MODE_STORY: Final = 0
ENT_CPU_FLAG: Final = 0x3E6                     # entity u8: non-zero = CPU controlled
ENT_TEAM: Final = 0x88                          # entity u8: 0 = the player's side

# Marker hook: the map screen hook. Its word is also what tells whether a DOL or a running game is patched.
MARKER_HOOK_ADDR: Final = 0x801A71F4            # last `bl` of the map screen init, after the HUD is built
MARKER_HOOK_VANILLA: Final = 0x480001E1         # bl MARKER_HOOK_DISPLACED_CALL
MARKER_HOOK_DISPLACED_CALL: Final = 0x801A73D4  # the call the hook replaces; counter_create performs it
MARKER_HOOK_RETURN: Final = MARKER_HOOK_ADDR + 4

# The other hooks, one instruction each
STORY_BORG_HOOK: Final = 0x8017FF60             # battle_load_player_force: `li r26, 0x615`
STORY_BORG_VANILLA: Final = 0x3B400615
STORY_BORG_VANILLA_ID: Final = 0x0615           # G Red, the borg deployed before the Gotcha Box is owned
GACHA_GRANT_HOOK: Final = 0x801CEBE0            # first instruction of reward_grant_dispatch
GACHA_GRANT_VANILLA: Final = 0x9421FFE0         # stwu r1, -0x20(r1)
GACHA_GRANT_RESUME: Final = GACHA_GRANT_HOOK + 4
ICON_TINT_HOOK_CURSOR: Final = 0x801AA434       # map_panel_row_update: bl sprite_set_color on a cursor move
ICON_TINT_VANILLA_CURSOR: Final = 0x4BFFD28D
ICON_TINT_HOOK_BLINK: Final = 0x801AA67C        # map_panel_row_update: bl sprite_set_color while a row blinks
ICON_TINT_VANILLA_BLINK: Final = 0x4BFFD045
GACHA_CREDIT_HOOK: Final = 0x8002F244           # kill_handler: `lbz r0, 0x3e6(r28)`, the gate of the gacha meter
GACHA_CREDIT_VANILLA: Final = 0x881C03E6

# Ui object types and glyphs
OBJ_TYPE_PANEL_ROW: Final = 0x21                # bar, icon and title objects of a map panel row
OBJ_TYPE_HUD: Final = 0x25                      # the digits use the HUD type, which the panel controller ignores
DIGIT_ANIM: Final = 0xA1                        # digit glyphs: frames 0-9 white, 10-19 yellow
GLYPH_FRAMES: Final = 20
YELLOW_GLYPH_OFFSET: Final = 10                 # frame of the yellow glyph of a digit
GLYPH_ONE: Final = 1                            # the "1" glyph, rotated into the "/"
SLASH_ROTATION: Final = -0x1800                 # OBJ_ROTATION_Z value that turns the "1" glyph into "/"
ROWS: Final = 5                                 # visible rows of the map panel
GLYPHS_PER_ROW: Final = 7                       # hundreds/tens/units of X, "/", hundreds/tens/units of Y
GLYPH_SLASH: Final = 3                          # the glyph in the middle of the row
GLYPH_Y_FIRST: Final = 4                        # the first glyph of Y: its hundreds
GLYPH_Y_TENS: Final = GLYPH_Y_FIRST + 1
DIGIT_COUNT: Final = ROWS * GLYPHS_PER_ROW
DESCRIPTOR_SIZE: Final = 0x14                   # ui object descriptor: anim u32, index u32, x/y/z floats
DESC_INDEX_ROW_STRIDE: Final = 16               # descriptor index = 16 * (row + 1) + GLYPH_INDEX_FIRST + glyph
DESC_INDEX_ROW_SHIFT: Final = 4
DESC_INDEX_ROW_MASK: Final = 0xF0
DESC_INDEX_GLYPH_MASK: Final = 0x0F
GLYPH_INDEX_ICON: Final = 1                     # the row's icon; its bar is index 0
GLYPH_INDEX_FIRST: Final = 8
SLASH_GLYPH_INDEX: Final = GLYPH_INDEX_FIRST + GLYPH_SLASH
DECIMAL_BASE: Final = 10
HUNDRED: Final = 100
SLOT_MIN: Final = -3                            # digit slots around the "/": -3..3
SLOT_MAX: Final = 3
SLOT_INDEX_BIAS: Final = -SLOT_MIN              # slot -> index into SLOT_FLOATS
FLOAT_SHIFT: Final = 2                          # index -> byte offset in a float table
AP_TABLE_ENTRY_SHIFT: Final = 1                 # chapter -> byte offset in AP_TABLE (2 bytes per chapter)
AP_TABLE_DONE_OFF: Final = 0
AP_TABLE_TOTAL_OFF: Final = 1
AP_FLAG_DONE: Final = 0x01
AP_FLAG_OUT_OF_LOGIC: Final = 0x02
TINT_PAIR_DONE: Final = 0                       # byte offset of each (selected, unselected) pair in AP_TINTS
TINT_PAIR_OUT_OF_LOGIC: Final = 8
TINT_PAIR_VANILLA: Final = 16
TINT_UNSELECTED_OFF: Final = 4                  # the unselected RGBA of a pair
SELECTED_ROW_COLOR: Final = -1                  # the color the game passes for the row under the cursor


def descriptor_index(row: int, glyph: int) -> int:
    """The descriptor index of a glyph.

    The row (from one) in the high nibble, the glyph after the bar and icon in the low.
    """
    return DESC_INDEX_ROW_STRIDE * (row + 1) + GLYPH_INDEX_FIRST + glyph


# Layout of the new section (loaded as text2)
LOAD_ADDR: Final = 0x80001810
COUNTER_CREATE: Final = LOAD_ADDR               # target of the map screen hook
COUNTER_UPDATE: Final = 0x80001910              # per-frame callback of every digit object
FRAME_FLOATS: Final = 0x80001F00                # GLYPH_FRAMES floats: frames 0..19
SLOT_FLOATS: Final = 0x80001F50                 # 7 floats: slots -3..3
X_OFFSET: Final = 0x80001F70                    # float: x of the "/" relative to the row bar
DIGIT_SPACING: Final = 0x80001F74               # float: distance between glyphs
Y_OFFSET: Final = 0x80001F78                    # float: y relative to the row bar
DIGIT_SCALE: Final = 0x80001F7C                 # float: scale of the digits
AP_TINTS: Final = 0x80001F80                    # 6 RGBA: done, out of logic, vanilla (selected/unselected each)
AP_STORY_BORG: Final = 0x80001F98               # u16, written by the client: borg id deployed without the Gotcha Box
AP_GACHA_SUPPRESS: Final = 0x80001F9A           # u8, written by the client: 1 = the game grants no reward
AP_GACHA_CREDIT: Final = 0x80001F9B             # u8, written by the client: 1 = the player's side feeds the gacha meter
STORY_BORG_ROUTINE: Final = 0x80001FA0
AP_TABLE: Final = 0x80002000                    # 256 x (done u8, total u8) per chapter, written by the client
AP_TABLE_SIZE: Final = 0x200
AP_FLAGS: Final = 0x80002200                    # 256 x u8 per chapter, from the client: bit0 done, bit1 out of logic
AP_FLAGS_SIZE: Final = 0x100
DIGIT_DESCRIPTORS: Final = 0x80002300           # DIGIT_COUNT descriptors of DESCRIPTOR_SIZE bytes
GACHA_SUPPRESS_ROUTINE: Final = 0x800025C0
COUNTER_STANDALONE: Final = 0x80002600          # callable (blr) variant of counter_create, for debugging
ICON_TINT_ROUTINE: Final = 0x80002700
GACHA_CREDIT_ROUTINE: Final = 0x80002800
ZONE_END: Final = 0x80002840
ZONE_SIZE: Final = ZONE_END - LOAD_ADDR
FREE_SECTION: Final = 2                         # text2 is empty in the vanilla DOL
GAME_ID: Final = b"GG4E08"
SWITCH_OFF: Final = b"\x00"                     # a client switch at rest

# Values baked into the data tables
DESC_X0: Final = 302.0                          # descriptor positions; counter_update rewrites x/y every frame
DESC_DX: Final = 26.0
DESC_Y0: Final = 210.0
DESC_DY: Final = -100.0
DESC_Z: Final = -1747.0
X_OFFSET_VALUE: Final = 330.0                   # anchors "X/Y" to the right edge of the bar, clear of long titles
DIGIT_SPACING_VALUE: Final = 26.0
Y_OFFSET_VALUE: Final = 0.0
DIGIT_SCALE_VALUE: Final = 0.55
TINT_DONE_SELECTED: Final = 0x44FF44FF          # completed: bright green in both cursor states
TINT_DONE_UNSELECTED: Final = 0x28C428FF
TINT_OUT_OF_LOGIC_SELECTED: Final = 0x30303038  # out of logic: translucent near-black, darker than the unselected row
TINT_OUT_OF_LOGIC_UNSELECTED: Final = 0x1C1C1C38
TINT_VANILLA_SELECTED: Final = 0xFFFFFFFF       # the game's own row colors, rewritten every frame: no tint sticks
TINT_VANILLA_UNSELECTED: Final = 0x888888FF
