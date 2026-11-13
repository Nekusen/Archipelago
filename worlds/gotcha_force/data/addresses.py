"""Every RAM address, offset, size and bit the client uses, by name: the only place they live.

``OFF_*`` offsets are relative to the progress block, ``SAVE_*`` and
``BOX2_*`` to the pointers of the live save copies.
"""

from typing import Final

GAME_ID_ADDR: Final = 0x80000000       # 6 bytes: disc game id
GAME_ID: Final = b"GG4E08"             # the USA disc, the only one supported
MEM1_LO: Final = 0x80000000            # console RAM start
MEM1_HI: Final = 0x81800000            # console RAM end: pointer check bound

POINTER_SIZE: Final = 4
U32_SIZE: Final = 4
U16_SIZE: Final = 2
NO_ID_BYTES: Final = bytes.fromhex("ffff")  # NO_ID as the game stores it
BYTE_MASK: Final = 0xFF

G_PROGRESS_PTR: Final = 0x80436354     # pointer to the progress block
SAVEDATA_PTR: Final = 0x80436220       # pointer to forces plus collection
BOX2_PTR: Final = 0x80436224           # pointer to overflow box plus fragments

INITIAL_FORCE_TABLE: Final = 0x804354E8  # s16 list: the player's initial force

NO_ID: Final = 0xFFFF              # u16: empty entry or list terminator
N_COMMANDERS: Final = 13           # commanders 1..13; 0 is the player
FIRST_COMMANDER: Final = 1

OFF_SCREEN: Final = 0x00           # u32: current screen
SCREEN_RESULTS: Final = 7          # OFF_SCREEN value of the results screen
OFF_BOX_FLAG: Final = 0x50         # u32: 1 = Gotcha Box unlocked
BOX_UNLOCKED: Final = 1
BOX_LOCKED: Final = 0
OFF_ROUTE: Final = 0x64            # u32: playthrough index, 0 first
ROUTE_MASK: Final = 0xFF           # only the low byte of the route is an index
OFF_GF_CAP: Final = 0x74           # u32: GF Energy cap
OFF_GF_CURRENT: Final = 0x78       # u32: current GF Energy, what the HUD draws
OFF_COMPANIONS: Final = 0x90       # u32: bit i = commander i recruited
OFF_UPGRADES: Final = 0x95         # 13 x u8: level of commander i at +i-1
OFF_ZONES: Final = 0x114           # u32: bit per map tile opened
OFF_MAP_STAGING: Final = 0x130     # 16 x u8 per tile; model ids at +0x10
MAP_STAGING_LEN: Final = 0x10      # bytes per array
MAP_STAGING_ARRAYS: Final = 2      # the two arrays zeroed: overlays and model ids
OFF_MAP_LISTS: Final = 0x174       # 13 x 0x40 u8: chapter of mission i
OFF_MAP_MAJORS: Final = 0x584      # 13 x 0x40 u8: major flag of mission i
OFF_MAP_COUNTS: Final = 0x574      # 13 x u8: valid missions per tile
MAP_TILE_SLOTS: Final = 0x40       # entries per tile in lists and majors
MAP_TILES: Final = 13              # tiles with a mission list
OFF_CURRENT_CHAPTER: Final = 0x9C8  # u32: chapter selected or in play
OFF_FLAGS64: Final = 0x1234        # 64 x u16 story flags
FLAGS64_LEN: Final = 128           # bytes of the flag array
STORY_FLAG_STRIDE: Final = 2       # bytes per story flag
STORY_FLAG_PLAYED: Final = 0x02    # bit1 of a story flag: event already played, the one bit kept
OFF_GACHA_WHOLE_COUNT: Final = 0x1504  # u32: prizes drawn as whole borgs
OFF_GACHA_PIECE_COUNT: Final = 0x1508  # u32: prizes drawn as pieces
OFF_GACHA_ACCUMULATORS: Final = 0x2D18  # u32: accumulators in use; 0 cuts the draw
OFF_GACHA_PRIZE_LATCH: Final = 0x4520  # u16: id of the prize being drawn
OFF_PERSISTENT: Final = 0x4524     # 8 x 32 B: chapters beaten, per route
PERSISTENT_LEN: Final = 32
OFF_CHAPTER_STATE: Final = 0xA34   # 8 B per chapter: bits, wins, defeats
CHAPTER_STATE_STRIDE: Final = 8
CHAPTER_STATE_FLAGS: Final = 0     # chapter byte 0: availability bits
CHAPTER_STATE_WINS: Final = 1      # chapter byte 1: win counter, the check signal
CHAPTER_AVAILABLE: Final = 0x01    # bit0 of the flags byte: listed on the map
CHAPTER_WON: Final = 0x02          # bit1 of the flags byte: already won (kept clear: missions repeat)
N_CHAPTERS: Final = 200            # chapter entries iterated

ZONES_ALL_MASK: Final = 0x3FFF     # bits 0..13: every zone and stage open

OFF_PARTNER_CURRENT: Final = 0xC4  # u8: partner of the map node, transient

BATTLE_PTR: Final = 0x80433934         # pointer to the battle struct
BATTLE_SLOTS: Final = 6                # slots per battle, 0 the player
PARTNER_BATTLE_SLOT: Final = 1         # the partner's slot
OFF_BATTLE_RESOLUTION: Final = 0x1F    # u8: 0 unresolved, then bits per team
BATTLE_UNRESOLVED: Final = 0
OFF_BATTLE_FINISHER: Final = 0xB4      # latch: entity of the decisive blow
SLOT_ENTITY_PTRS: Final = 0x803C4E84   # 6 x u32: entity of each battle slot
OFF_ENT_OWN_LOSSES: Final = 0x435      # entity u8: losses suffered by the slot
OFF_BATTLE_ALLY_METER: Final = 0x114   # u32: initial cost of the own force
OFF_BATTLE_COMMANDER: Final = 0x20     # + slot, u8: commander, 0 the player
OFF_BATTLE_SLOT_TEAM: Final = 0xCB     # + slot, u8: 0 ally, 1 enemy
TEAM_PLAYER_SIDE: Final = 0
OFF_BATTLE_QUOTA: Final = 0x5A         # + slot, s8: borgs the slot deploys
OFF_BATTLE_FORCE: Final = 0x1E8        # + slot * stride: the slot's force
BATTLE_FORCE_ENTRY: Final = 0x1C       # bytes per entry, u16 id at +0
BATTLE_FORCE_SLOTS: Final = 30         # entries per force list

SAVE_FORCES: Final = 0x0000        # 20 saved forces
FORCE_SLOTS: Final = 20
FORCE_ENTRY: Final = 0x6C          # bytes per saved force
FORCE_COST_OFF: Final = 0x2C       # force u32: cached total cost
FORCE_INDICES_OFF: Final = 0x30    # force 30 x s16: collection indices
FORCE_INDICES: Final = 30
SAVE_COLLECTION: Final = 0x0870    # 200 collection entries
COLLECTION_SLOTS: Final = 200      # entries before the overflow box
COLLECTION_ENTRY: Final = 0x20     # bytes per entry, u16 id at +0
COLLECTION_LEVELS_OFF: Final = 2   # entry 2 x u8: level when obtained, level gained
COLLECTION_LEVELS_LEN: Final = 2
COLLECTION_INITIAL_LEVEL: Final = 1  # the level a new entry is obtained at
COLLECTION_SERIAL_OFF: Final = 4   # entry u32: serial
COLLECTION_EXP_OFF: Final = 8      # entry u32: experience
COLLECTION_GACHA_FLAG_OFF: Final = 0x0C  # entry u8: 1 = obtained via gacha
OBTAINED_VIA_GACHA: Final = 1
NEW_GAME_ENTRY: Final = 0          # the collection entry a new game creates, G Red
SAVE_N_FORCES: Final = 0x2170      # u16: saved forces
SAVE_N_BORGS: Final = 0x2172       # u16: borgs in the collection

BOX2_OVERFLOW: Final = 0x0000      # 2000 overflow entries, u16 id at +0
OVERFLOW_SLOTS: Final = 2000
OVERFLOW_ENTRY: Final = 0x10       # bytes per overflow entry
BOX2_FRAGMENTS: Final = 0x7D00     # 1000 fragment entries
FRAG_SLOTS: Final = 1000
FRAG_ENTRY: Final = 0x0C           # bytes per fragment entry, u16 id at +0
FRAG_PIECE_OFF: Final = 2          # fragment u8: piece number
FRAG_NEW_FLAG: Final = 1           # fragment u8 at +8: 1 = new
BOX2_N_FRAGMENTS: Final = 0xABE2   # u16: fragments stored

QREC_DELAYS: Final = 0x00          # queue record: 2 x s16 spawn delays
QREC_CAP: Final = 0x04             # s16: live-slot cap
QREC_CAP_MAX: Final = 5
QREC_ID: Final = 0x08              # u16: borg id, the spawn cell
QREC_FLAGS: Final = 0x0E           # u8: behaviour flags
QREC_TARGET: Final = 0x10          # u8: 1 = mission target
QREC_POS: Final = 0x14             # 3 x f32: position
QREC_LOOP_MARK_OFF: Final = 0      # loop record: s16 mark
QREC_LOOP_BACK_OFF: Final = 2      # loop record: s16 records to go back
STAGE_ENTRY: Final = 16            # bytes per STAGE_OBJ_TABLE entry: 4 u32
STAGE_QUEUE2_OFF: Final = 8        # u32: pointer to enemy queue 2

AP_STORY_BORG: Final = 0x80001F98      # u16: story borg id read by the patch

AP_GACHA_SUPPRESS: Final = 0x80001F9A  # u8: 1 = the gacha grants nothing
GACHA_GRANT_HOOK: Final = 0x801CEBE0   # hooked word of reward_grant_dispatch

AP_GACHA_CREDIT: Final = 0x80001F9B    # u8: 1 = own side kills feed the meter
GACHA_CREDIT_HOOK: Final = 0x8002F244  # hooked word of kill_handler

SWITCH_ON: Final = b"\x01"             # the patch's u8 switches
SWITCH_OFF: Final = b"\x00"

AP_TINTS: Final = 0x80001F80           # 4 x RGBA: row icon tints, per tick
AP_TINTS_BYTES: Final = bytes.fromhex(
    "44ff44ff28c428ff"             # completed: selected, unselected
    "303030381c1c1c38"
)            # out of logic: selected, unselected

AP_TABLE: Final = 0x80002000       # 256 x (done u8, total u8) per chapter
AP_TABLE_LEN: Final = 0x200
AP_TABLE_ENTRY: Final = 2         # done u8 first, then the total
AP_TABLE_TOTAL_OFF: Final = 1
AP_TABLE_MAX_COUNT: Final = 0xFF   # a counter byte saturates here
AP_FLAGS: Final = 0x80002200       # 256 x u8 per chapter
AP_FLAGS_LEN: Final = 0x100
AP_FLAG_DONE: Final = 0x01
AP_FLAG_OUT_OF_LOGIC: Final = 0x02
