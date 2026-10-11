"""src/core/platform/__init__.py

OSプラットフォーム抽象レイヤー。
"""

from __future__ import annotations

import sys
from typing import Any

from src.core.platform.protocols import (
    HotkeyListener,
    PasteSender,
    ProcessInspector,
    SingleInstanceController,
    SoundPlayer,
)


def get_platform_adapters() -> dict[str, Any]:
    """現在のOSに応じた具象またはNullプラットフォームアダプターを返す。"""
    if sys.platform == "win32":
        from src.core.platform.windows import (
            WindowsPasteSender,
            WindowsProcessInspector,
            WindowsSingleInstanceController,
            WindowsSoundPlayer,
        )

        return {
            "process_inspector": WindowsProcessInspector(),
            "single_instance": WindowsSingleInstanceController(),
            "sound_player": WindowsSoundPlayer(),
            "paste_sender": WindowsPasteSender(),
        }
    else:
        from src.core.platform.null import (
            NullPasteSender,
            NullProcessInspector,
            NullSingleInstanceController,
            NullSoundPlayer,
        )

        return {
            "process_inspector": NullProcessInspector(),
            "single_instance": NullSingleInstanceController(),
            "sound_player": NullSoundPlayer(),
            "paste_sender": NullPasteSender(),
        }


__all__ = [
    "ProcessInspector",
    "SingleInstanceController",
    "SoundPlayer",
    "PasteSender",
    "HotkeyListener",
    "get_platform_adapters",
]
