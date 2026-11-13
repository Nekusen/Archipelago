from __future__ import annotations

from collections.abc import Iterable, Mapping

from ..data.borgs import CYBER_DEATH_DRAGON, CYBER_DRAGON, DEATH_BORGS, DEATH_HEAD
from ..data.gacha import GACHA_REGISTERS, THRESHOLD_COUNT, UNOBTAINABLE, GachaRegister
from ..data.spawns import SPAWNS

KILL_REDIRECT = {CYBER_DEATH_DRAGON: (DEATH_HEAD, CYBER_DRAGON)}

DEATH_BORG_NORMALIZER = 10

MIN_THRESHOLD = 1

MIN_DIVISOR = 1

UNSCALED_RATE = 1

EXHAUSTED = (UNOBTAINABLE,) * THRESHOLD_COUNT


def gacha_chapters(assignments: Mapping[int, int | None],
                   chapter_pool: Iterable[int],
                   extra: Mapping[int, Iterable[int]] | None = None,
                   ) -> dict[int, set[int]]:
    out: dict[int, set[int]] = {}
    for chapter in chapter_pool:
        finals = [assignments.get(addr, borg_id)
                  for addr, borg_id, *_ in SPAWNS.get(chapter, ())]
        if extra:
            finals.extend(extra.get(chapter, ()))
        for final in finals:
            if final is None:
                continue
            for target in KILL_REDIRECT.get(final, (final,)):
                register = GACHA_REGISTERS.get(target)
                if register is None or not _pays_out(register):
                    continue
                out.setdefault(target, set()).add(chapter)
    return out


def _pays_out(register: GachaRegister) -> bool:
    return any(threshold >= 0 for threshold in register.thresholds)


def thresholds_for(borg_id: int, vanilla: tuple[int, ...],
                   rate: int) -> tuple[int, ...]:
    return scaled_thresholds(
        vanilla, rate,
        DEATH_BORG_NORMALIZER if is_death_borg(borg_id) else 1
    )


def scaled_thresholds(vanilla: tuple[int, ...], rate: int,
                      normalizer: int = 1) -> tuple[int, ...]:
    div = max(rate, MIN_DIVISOR) * max(normalizer, MIN_DIVISOR)
    return tuple(u if u < 0 else max(MIN_THRESHOLD, u // div) for u in vanilla)


def is_death_borg(borg_id: int) -> bool:
    return borg_id in DEATH_BORGS
