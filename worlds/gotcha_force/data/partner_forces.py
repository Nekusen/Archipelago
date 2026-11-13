"""Generated from the game's data tables. Do not edit by hand."""

from typing import NamedTuple


class PartnerSlot(NamedTuple):
    cell: int    # u16 address of the borg id
    borg: int    # vanilla id


# companion -> upgrade levels -> the slots of its force; the last slot of each
# list is the companion's ace. Each list has a fixed capacity: never write more
# borgs than vanilla (with fewer, the 0xFFFF terminator moves up).
PARTNER_FORCES: dict[int, tuple[tuple[PartnerSlot, ...], ...]] = {
    1: (
        (PartnerSlot(0x804354f0, 0x000a),),
        (
            PartnerSlot(0x8035addc, 0x0000), PartnerSlot(0x8035adde, 0x0003), PartnerSlot(0x8035ade0, 0x0000),
            PartnerSlot(0x8035ade2, 0x000a),
        ),
        (
            PartnerSlot(0x8035ade8, 0x0000), PartnerSlot(0x8035adea, 0x0003), PartnerSlot(0x8035adec, 0x0000),
            PartnerSlot(0x8035adee, 0x0000), PartnerSlot(0x8035adf0, 0x000a),
        ),
        (
            PartnerSlot(0x8035adf4, 0x0003), PartnerSlot(0x8035adf6, 0x0000), PartnerSlot(0x8035adf8, 0x0003),
            PartnerSlot(0x8035adfa, 0x0001), PartnerSlot(0x8035adfc, 0x000a),
        ),
        (
            PartnerSlot(0x8035ae00, 0x0000), PartnerSlot(0x8035ae02, 0x0003), PartnerSlot(0x8035ae04, 0x0000),
            PartnerSlot(0x8035ae06, 0x0003), PartnerSlot(0x8035ae08, 0x0000), PartnerSlot(0x8035ae0a, 0x0003),
            PartnerSlot(0x8035ae0c, 0x0001), PartnerSlot(0x8035ae0e, 0x000a),
        ),
        (
            PartnerSlot(0x8035ae14, 0x0003), PartnerSlot(0x8035ae16, 0x0000), PartnerSlot(0x8035ae18, 0x0003),
            PartnerSlot(0x8035ae1a, 0x0001), PartnerSlot(0x8035ae1c, 0x0003), PartnerSlot(0x8035ae1e, 0x0007),
            PartnerSlot(0x8035ae20, 0x000a),
        ),
        (
            PartnerSlot(0x8035ae24, 0x0006), PartnerSlot(0x8035ae26, 0x0007), PartnerSlot(0x8035ae28, 0x0601),
            PartnerSlot(0x8035ae2a, 0x000a),
        ),
    ),
    2: (
        (PartnerSlot(0x804354f4, 0x090d),),
        (PartnerSlot(0x804354f8, 0x0900), PartnerSlot(0x804354fa, 0x090d)),
        (PartnerSlot(0x80435500, 0x0900), PartnerSlot(0x80435502, 0x0903), PartnerSlot(0x80435504, 0x090d)),
        (
            PartnerSlot(0x8035ae50, 0x0903), PartnerSlot(0x8035ae52, 0x0900), PartnerSlot(0x8035ae54, 0x0904),
            PartnerSlot(0x8035ae56, 0x090d),
        ),
        (
            PartnerSlot(0x8035ae5c, 0x0903), PartnerSlot(0x8035ae5e, 0x0900), PartnerSlot(0x8035ae60, 0x0902),
            PartnerSlot(0x8035ae62, 0x0904), PartnerSlot(0x8035ae64, 0x090d),
        ),
        (
            PartnerSlot(0x8035ae68, 0x090a), PartnerSlot(0x8035ae6a, 0x0900), PartnerSlot(0x8035ae6c, 0x0902),
            PartnerSlot(0x8035ae6e, 0x0901), PartnerSlot(0x8035ae70, 0x0904), PartnerSlot(0x8035ae72, 0x090d),
        ),
        (
            PartnerSlot(0x8035ae78, 0x0900), PartnerSlot(0x8035ae7a, 0x0908), PartnerSlot(0x8035ae7c, 0x0900),
            PartnerSlot(0x8035ae7e, 0x0908), PartnerSlot(0x8035ae80, 0x0900), PartnerSlot(0x8035ae82, 0x0908),
            PartnerSlot(0x8035ae84, 0x090d),
        ),
    ),
    3: (
        (PartnerSlot(0x80435508, 0x0a09),),
        (PartnerSlot(0x8043550c, 0x0a00), PartnerSlot(0x8043550e, 0x0a09)),
        (PartnerSlot(0x80435514, 0x0a01), PartnerSlot(0x80435516, 0x0a09)),
        (PartnerSlot(0x8043551c, 0x0a01), PartnerSlot(0x8043551e, 0x0a06), PartnerSlot(0x80435520, 0x0a09)),
        (PartnerSlot(0x80435524, 0x0a03), PartnerSlot(0x80435526, 0x0a08), PartnerSlot(0x80435528, 0x0a09)),
        (PartnerSlot(0x8043552c, 0x0a08), PartnerSlot(0x8043552e, 0x0a04), PartnerSlot(0x80435530, 0x0a09)),
        (PartnerSlot(0x80435534, 0x0a04), PartnerSlot(0x80435536, 0x0a09), PartnerSlot(0x80435538, 0x0608)),
    ),
    4: (
        (PartnerSlot(0x8043553c, 0x0709),),
        (PartnerSlot(0x80435540, 0x0700), PartnerSlot(0x80435542, 0x0709)),
        (PartnerSlot(0x80435548, 0x0700), PartnerSlot(0x8043554a, 0x020a), PartnerSlot(0x8043554c, 0x0709)),
        (PartnerSlot(0x80435550, 0x0700), PartnerSlot(0x80435552, 0x0200), PartnerSlot(0x80435554, 0x0709)),
        (
            PartnerSlot(0x8035aec8, 0x0700), PartnerSlot(0x8035aeca, 0x0200), PartnerSlot(0x8035aecc, 0x0704),
            PartnerSlot(0x8035aece, 0x0709),
        ),
        (
            PartnerSlot(0x8035aed4, 0x0700), PartnerSlot(0x8035aed6, 0x0200), PartnerSlot(0x8035aed8, 0x0703),
            PartnerSlot(0x8035aeda, 0x0704), PartnerSlot(0x8035aedc, 0x0709),
        ),
        (
            PartnerSlot(0x8035aee0, 0x0706), PartnerSlot(0x8035aee2, 0x020e), PartnerSlot(0x8035aee4, 0x0704),
            PartnerSlot(0x8035aee6, 0x0709),
        ),
    ),
    5: (
        (PartnerSlot(0x80435558, 0x0108),),
        (PartnerSlot(0x8043555c, 0x0100), PartnerSlot(0x8043555e, 0x0108)),
        (PartnerSlot(0x80435564, 0x0101), PartnerSlot(0x80435566, 0x0108)),
        (PartnerSlot(0x8043556c, 0x0100), PartnerSlot(0x8043556e, 0x0102), PartnerSlot(0x80435570, 0x0108)),
        (PartnerSlot(0x80435574, 0x0102), PartnerSlot(0x80435576, 0x0104), PartnerSlot(0x80435578, 0x0108)),
        (
            PartnerSlot(0x8035af0c, 0x0100), PartnerSlot(0x8035af0e, 0x0102), PartnerSlot(0x8035af10, 0x0101),
            PartnerSlot(0x8035af12, 0x0104), PartnerSlot(0x8035af14, 0x0108),
        ),
        (
            PartnerSlot(0x8035af18, 0x0102), PartnerSlot(0x8035af1a, 0x0104), PartnerSlot(0x8035af1c, 0x0600),
            PartnerSlot(0x8035af1e, 0x0108),
        ),
    ),
    6: (
        (PartnerSlot(0x8043557c, 0x0c06),),
        (PartnerSlot(0x80435580, 0x0c06),),
        (PartnerSlot(0x80435584, 0x0c00), PartnerSlot(0x80435586, 0x0c06)),
        (PartnerSlot(0x8043558c, 0x0d04), PartnerSlot(0x8043558e, 0x0c00), PartnerSlot(0x80435590, 0x0c06)),
        (PartnerSlot(0x80435594, 0x0d04), PartnerSlot(0x80435596, 0x0c01), PartnerSlot(0x80435598, 0x0c06)),
        (
            PartnerSlot(0x8035af44, 0x0d05), PartnerSlot(0x8035af46, 0x0c00), PartnerSlot(0x8035af48, 0x0c02),
            PartnerSlot(0x8035af4a, 0x0c06),
        ),
        (
            PartnerSlot(0x8035af50, 0x0d05), PartnerSlot(0x8035af52, 0x0c02), PartnerSlot(0x8035af54, 0x0604),
            PartnerSlot(0x8035af56, 0x0c06),
        ),
    ),
    7: (
        (PartnerSlot(0x8043559c, 0x070a),),
        (PartnerSlot(0x804355a0, 0x0702), PartnerSlot(0x804355a2, 0x070a)),
        (PartnerSlot(0x804355a8, 0x0702), PartnerSlot(0x804355aa, 0x0201), PartnerSlot(0x804355ac, 0x070a)),
        (PartnerSlot(0x804355b0, 0x0702), PartnerSlot(0x804355b2, 0x0201), PartnerSlot(0x804355b4, 0x070a)),
        (
            PartnerSlot(0x8035af7c, 0x0702), PartnerSlot(0x8035af7e, 0x0201), PartnerSlot(0x8035af80, 0x020c),
            PartnerSlot(0x8035af82, 0x070a),
        ),
        (
            PartnerSlot(0x8035af88, 0x0702), PartnerSlot(0x8035af8a, 0x020c), PartnerSlot(0x8035af8c, 0x0201),
            PartnerSlot(0x8035af8e, 0x020d), PartnerSlot(0x8035af90, 0x070a),
        ),
        (
            PartnerSlot(0x8035af94, 0x0201), PartnerSlot(0x8035af96, 0x0203), PartnerSlot(0x8035af98, 0x0208),
            PartnerSlot(0x8035af9a, 0x0204), PartnerSlot(0x8035af9c, 0x070a),
        ),
    ),
    8: (
        (PartnerSlot(0x804355b8, 0x040a),),
        (PartnerSlot(0x804355bc, 0x0400), PartnerSlot(0x804355be, 0x040a)),
        (PartnerSlot(0x804355c4, 0x0405), PartnerSlot(0x804355c6, 0x0400), PartnerSlot(0x804355c8, 0x040a)),
        (
            PartnerSlot(0x8035afc0, 0x0400), PartnerSlot(0x8035afc2, 0x0405), PartnerSlot(0x8035afc4, 0x0404),
            PartnerSlot(0x8035afc6, 0x040a),
        ),
        (
            PartnerSlot(0x8035afcc, 0x0400), PartnerSlot(0x8035afce, 0x0405), PartnerSlot(0x8035afd0, 0x0404),
            PartnerSlot(0x8035afd2, 0x0401), PartnerSlot(0x8035afd4, 0x040a),
        ),
        (
            PartnerSlot(0x8035afd8, 0x0400), PartnerSlot(0x8035afda, 0x0405), PartnerSlot(0x8035afdc, 0x0404),
            PartnerSlot(0x8035afde, 0x0401), PartnerSlot(0x8035afe0, 0x0403), PartnerSlot(0x8035afe2, 0x040a),
        ),
        (
            PartnerSlot(0x8035afe8, 0x0401), PartnerSlot(0x8035afea, 0x0403), PartnerSlot(0x8035afec, 0x0627),
            PartnerSlot(0x8035afee, 0x040a),
        ),
    ),
    9: (
        (PartnerSlot(0x804355cc, 0x000b),),
        (PartnerSlot(0x804355d0, 0x0002), PartnerSlot(0x804355d2, 0x000b)),
        (PartnerSlot(0x804355d8, 0x0002), PartnerSlot(0x804355da, 0x0103), PartnerSlot(0x804355dc, 0x000b)),
        (PartnerSlot(0x804355e0, 0x0002), PartnerSlot(0x804355e2, 0x0d02), PartnerSlot(0x804355e4, 0x000b)),
        (
            PartnerSlot(0x8035b014, 0x0002), PartnerSlot(0x8035b016, 0x0d02), PartnerSlot(0x8035b018, 0x050d),
            PartnerSlot(0x8035b01a, 0x000b),
        ),
        (
            PartnerSlot(0x8035b020, 0x0103), PartnerSlot(0x8035b022, 0x0517), PartnerSlot(0x8035b024, 0x0002),
            PartnerSlot(0x8035b026, 0x0501), PartnerSlot(0x8035b028, 0x000b),
        ),
        (
            PartnerSlot(0x8035b02c, 0x050b), PartnerSlot(0x8035b02e, 0x0501), PartnerSlot(0x8035b030, 0x0516),
            PartnerSlot(0x8035b032, 0x000b),
        ),
    ),
    10: (
        (PartnerSlot(0x804355e8, 0x0e05),),
        (PartnerSlot(0x804355ec, 0x0e05),),
        (PartnerSlot(0x804355f0, 0x0e05),),
        (PartnerSlot(0x804355f4, 0x0e05),),
        (PartnerSlot(0x804355f8, 0x0e05),),
        (PartnerSlot(0x804355fc, 0x0e01), PartnerSlot(0x804355fe, 0x0e05)),
        (PartnerSlot(0x80435604, 0x0e03), PartnerSlot(0x80435606, 0x0e05)),
    ),
    11: (
        (PartnerSlot(0x8043560c, 0x030b),),
        (PartnerSlot(0x80435610, 0x0300), PartnerSlot(0x80435612, 0x0b04), PartnerSlot(0x80435614, 0x030b)),
        (
            PartnerSlot(0x8035b078, 0x0301), PartnerSlot(0x8035b07a, 0x0b01), PartnerSlot(0x8035b07c, 0x0306),
            PartnerSlot(0x8035b07e, 0x030b),
        ),
        (
            PartnerSlot(0x8035b084, 0x0301), PartnerSlot(0x8035b086, 0x0b01), PartnerSlot(0x8035b088, 0x0306),
            PartnerSlot(0x8035b08a, 0x0302), PartnerSlot(0x8035b08c, 0x030b),
        ),
        (
            PartnerSlot(0x8035b090, 0x0306), PartnerSlot(0x8035b092, 0x0b00), PartnerSlot(0x8035b094, 0x0302),
            PartnerSlot(0x8035b096, 0x0305), PartnerSlot(0x8035b098, 0x030b),
        ),
        (
            PartnerSlot(0x8035b09c, 0x0302), PartnerSlot(0x8035b09e, 0x0b00), PartnerSlot(0x8035b0a0, 0x0305),
            PartnerSlot(0x8035b0a2, 0x030a), PartnerSlot(0x8035b0a4, 0x030b),
        ),
        (
            PartnerSlot(0x8035b0a8, 0x0b00), PartnerSlot(0x8035b0aa, 0x030a), PartnerSlot(0x8035b0ac, 0x0b06),
            PartnerSlot(0x8035b0ae, 0x0609), PartnerSlot(0x8035b0b0, 0x030b),
        ),
    ),
    12: (
        (PartnerSlot(0x80435618, 0x080e),),
        (PartnerSlot(0x8043561c, 0x0805), PartnerSlot(0x8043561e, 0x080e)),
        (PartnerSlot(0x80435624, 0x0806), PartnerSlot(0x80435626, 0x080e)),
        (PartnerSlot(0x8043562c, 0x0805), PartnerSlot(0x8043562e, 0x0806), PartnerSlot(0x80435630, 0x080e)),
        (
            PartnerSlot(0x8035b0d4, 0x0805), PartnerSlot(0x8035b0d6, 0x0806), PartnerSlot(0x8035b0d8, 0x0805),
            PartnerSlot(0x8035b0da, 0x0800), PartnerSlot(0x8035b0dc, 0x080e),
        ),
        (
            PartnerSlot(0x8035b0e0, 0x0805), PartnerSlot(0x8035b0e2, 0x0806), PartnerSlot(0x8035b0e4, 0x0801),
            PartnerSlot(0x8035b0e6, 0x080d), PartnerSlot(0x8035b0e8, 0x0809), PartnerSlot(0x8035b0ea, 0x080e),
        ),
        (
            PartnerSlot(0x8035b0f0, 0x0806), PartnerSlot(0x8035b0f2, 0x0808), PartnerSlot(0x8035b0f4, 0x0d06),
            PartnerSlot(0x8035b0f6, 0x0804), PartnerSlot(0x8035b0f8, 0x0809), PartnerSlot(0x8035b0fa, 0x080e),
        ),
    ),
    13: (
        (PartnerSlot(0x80435634, 0x0a07),),
        (PartnerSlot(0x80435638, 0x0005), PartnerSlot(0x8043563a, 0x0a07)),
        (PartnerSlot(0x80435640, 0x0701), PartnerSlot(0x80435642, 0x0a07)),
        (PartnerSlot(0x80435648, 0x0202), PartnerSlot(0x8043564a, 0x0a07)),
        (PartnerSlot(0x80435650, 0x0005), PartnerSlot(0x80435652, 0x0202), PartnerSlot(0x80435654, 0x0a07)),
        (
            PartnerSlot(0x8035b120, 0x0708), PartnerSlot(0x8035b122, 0x0005), PartnerSlot(0x8035b124, 0x0202),
            PartnerSlot(0x8035b126, 0x0a07),
        ),
        (
            PartnerSlot(0x8035b12c, 0x0205), PartnerSlot(0x8035b12e, 0x0510), PartnerSlot(0x8035b130, 0x0511),
            PartnerSlot(0x8035b132, 0x0a07),
        ),
    ),
}
