"""src/core/platform/__init__.py

OSプラットフォーム抽象レイヤー。
"""

from src.core.platform.protocols import (
    HotkeyListener,
    PasteSender,
    ProcessInspector,
    SingleInstanceController,
    SoundPlayer,
)

__all__ = [
    "ProcessInspector",
    "SingleInstanceController",
    "SoundPlayer",
    "PasteSender",
    "HotkeyListener",
]
