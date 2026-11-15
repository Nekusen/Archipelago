from __future__ import annotations

from typing import TYPE_CHECKING, Final

from CommonClient import ClientCommandProcessor, logger

if TYPE_CHECKING:
    from . import GotchaForceContext

SCOPE_ALL: Final = "all"

CHECKS_OUT_OF_LOGIC_MARK: Final = " !"


class GotchaForceCommandProcessor(ClientCommandProcessor):
    ctx: GotchaForceContext

    def _cmd_dolphin(self) -> None:
        """State of the connection with Dolphin."""
        ctx = self.ctx
        state = "connected" if ctx.dolphin.is_connected() else "disconnected"
        logger.info(f"Dolphin: {state}; valid game: {ctx.game_valid}")
