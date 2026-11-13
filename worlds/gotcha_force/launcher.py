from __future__ import annotations

import logging
import os
from typing import Final

from worlds.LauncherComponents import (
    Component,
    Type,
    components,
)
from worlds.LauncherComponents import launch as launch_component

from .game import CLIENT_NAME, GAME_NAME

PATCHER_TITLE: Final = "Gotcha Force ISO Patcher"


def _launch_client(*args: str) -> None:
    from .client import launch

    launch_component(launch, name=CLIENT_NAME, args=args)


def _patch_iso(*args: str) -> None:
    from .iso_patch import (
        AlreadyPatchedError,
        IsoPatchError,
        OutdatedPatchError,
        default_output,
        patch_iso,
    )

    iso_path = args[0] if args else _ask_for_iso()
    if not iso_path:
        logging.info("No ISO selected; nothing was patched.")
        return
    existed = os.path.exists(default_output(iso_path))
    try:
        patched_path = patch_iso(iso_path)
    except AlreadyPatchedError as e:
        _report(str(e), logging.INFO)
    except OutdatedPatchError as e:
        _report(str(e), logging.WARNING)
    except IsoPatchError as e:
        _report(str(e), logging.ERROR, error=True)
    except Exception as e:
        logging.exception(e)
        _report(f"Unexpected error while patching:\n{e}", None, error=True)
    else:
        _report(_done_message(patched_path, existed), logging.INFO)


def _ask_for_iso() -> str | None:
    import Utils

    return Utils.open_filename(
        "Select your clean Gotcha Force USA ISO (GG4E08)",
        (("GameCube ISO", (".iso", ".gcm")),)
    )


def _report(message: str, level: int | None, error: bool = False) -> None:
    import Utils

    if level is not None:
        logging.log(level, message)
    Utils.messagebox(PATCHER_TITLE, message, error=error)


def _done_message(patched_path: str, existed: bool) -> str:
    action = "updated" if existed else "created"
    return (f"Done! Patched copy {action}:\n{patched_path}\n\n"
            "Open this copy in Dolphin to play. It works for every "
            "seed; run this patcher again only after updating the "
            "apworld. Your original ISO was not changed.")


components.append(Component(
    "Gotcha Force Client",
    func=_launch_client,
    component_type=Type.CLIENT,
    game_name=GAME_NAME,
    supports_uri=True,
))

components.append(Component(
    PATCHER_TITLE,
    func=_patch_iso,
    component_type=Type.TOOL,
    description="Create the patched copy of your Gotcha Force USA ISO "
                "(adds the on-map mission status display).",
))
