"""keystone front end: expands the source conventions of asm/*.s and checks that no branch leaves its block."""

import re
from typing import Final

from keystone import KS_ARCH_PPC, KS_MODE_BIG_ENDIAN, KS_MODE_PPC32, Ks

_RE_CALL: Final = re.compile(r"^\s*(call|jump)\s+([A-Z_][A-Z0-9_]*)\s*$")
_RE_HI: Final = re.compile(r"\bhi\(([A-Z_][A-Z0-9_]*)\)")
_RE_LO: Final = re.compile(r"\blo\(([A-Z_][A-Z0-9_]*)\)")
_RE_SYM: Final = re.compile(r"\$([A-Z_][A-Z0-9_]*)")

#: the two halves of a 32-bit address, as `lis` and `addi` take them
_HALF_SHIFT: Final = 16
_HALF_MASK: Final = 0xFFFF
_HALF_SIGN: Final = 0x8000
_HALF_RANGE: Final = 0x10000
_WORD_MASK: Final = 0xFFFFFFFF

#: PowerPC branch encodings: the opcode field, the two branch opcodes and the displacement fields
_INSTRUCTION_SIZE: Final = 4
_OPCODE_SHIFT: Final = 26
_OPCODE_BRANCH: Final = 18
_OPCODE_BRANCH_CONDITIONAL: Final = 16
_B_WORD: Final = 0x48000000
_B_LINK: Final = 0x00000001
_B_DISP_MASK: Final = 0x03FFFFFC
_B_SIGN: Final = 0x02000000
_BC_DISP_MASK: Final = 0xFFFC
_BC_SIGN: Final = 0x8000

#: the call and jump directives of the sources
_CALL: Final = "call"


def high_half(addr: int) -> int:
    """Upper half for `lis`, adjusted so that `addi` with the signed lower half lands on addr."""
    return ((addr >> _HALF_SHIFT) + (1 if addr & _HALF_SIGN else 0)) & _HALF_MASK


def low_half(addr: int) -> int:
    """Signed lower half for `addi` and the displacement of loads and stores."""
    low = addr & _HALF_MASK
    return low - _HALF_RANGE if low & _HALF_SIGN else low


def absolute_branch(target: int, link: bool) -> list[str]:
    """lis/addi r12 + mtctr + bctrl (or bctr).

    keystone can encode `bl` to an absolute address with a wrong target and
    no error, so the sources never use one: every call or jump out of a
    block goes through the count register.
    """
    return [f"lis 12, {high_half(target):#x}",
            f"addi 12, 12, {low_half(target)}",
            "mtctr 12",
            "bctrl" if link else "bctr"]


def branch_word(origin: int, target: int, link: bool) -> int:
    """Word of a relative `b`/`bl` at origin, computed by hand for the same reason."""
    word = _B_WORD | ((target - origin) & _B_DISP_MASK)
    return word | _B_LINK if link else word


def _expand_line(code: str, symbols: dict[str, int]) -> list[str]:
    """The keystone lines of one source line: a call or jump expanded, else hi()/lo()/$NAME resolved."""
    call = _RE_CALL.match(code)
    if call:
        directive, symbol = call.groups()
        return [f"    {line}" for line in absolute_branch(symbols[symbol], link=directive == _CALL)]
    code = _RE_HI.sub(lambda match: hex(high_half(symbols[match.group(1)])), code)
    code = _RE_LO.sub(lambda match: str(low_half(symbols[match.group(1)])), code)
    code = _RE_SYM.sub(lambda match: str(symbols[match.group(1)]), code)
    return [code]


def expand(source: str, symbols: dict[str, int]) -> str:
    """Plain keystone text from a source: comments dropped, hi()/lo()/$NAME resolved, call/jump expanded."""
    out = []
    for line in source.splitlines():
        code = line.split("#", 1)[0].rstrip()
        if code.strip():
            out.extend(_expand_line(code, symbols))
    return "".join(f"{line}\n" for line in out)


def _branch_displacement(word: int) -> int | None:
    """The signed displacement of a branch word; None for any other instruction."""
    opcode = word >> _OPCODE_SHIFT
    if opcode == _OPCODE_BRANCH:
        disp = word & _B_DISP_MASK
        return disp - (_B_SIGN << 1) if disp & _B_SIGN else disp
    if opcode == _OPCODE_BRANCH_CONDITIONAL:
        disp = word & _BC_DISP_MASK
        return disp - (_BC_SIGN << 1) if disp & _BC_SIGN else disp
    return None


def check_branches(code: bytes, base: int, name: str) -> None:
    """Every b/bl and every conditional branch must land inside [base, base + len)."""
    for offset in range(0, len(code), _INSTRUCTION_SIZE):
        disp = _branch_displacement(int.from_bytes(code[offset:offset + _INSTRUCTION_SIZE], "big"))
        if disp is None:
            continue
        target = (base + offset + disp) & _WORD_MASK
        if not base <= target < base + len(code):
            raise ValueError(f"{name}: branch at {base + offset:#x} leaves the block (-> {target:#x})")


def assemble(source: str, base: int, symbols: dict[str, int], name: str) -> bytes:
    """Bytes of one block placed at base."""
    keystone = Ks(KS_ARCH_PPC, KS_MODE_PPC32 | KS_MODE_BIG_ENDIAN)
    encoding, _count = keystone.asm(expand(source, symbols), base)
    code = bytes(encoding or [])
    if not code:
        raise ValueError(f"{name}: nothing assembled")
    check_branches(code, base, name)
    return code
