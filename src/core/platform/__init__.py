"""src/core/platform/__init__.py

OSプラットフォーム抽象レイヤー。

どの OS でどの実装を使うかの選択は ``PlatformServices`` に集約する。
非対応の機能を取得しようとすると ``UnsupportedFeatureError`` を送出する。
"""

from __future__ import annotations

from src.core.platform.errors import (
    PlatformError,
    SingleInstanceError,
    UnsupportedFeatureError,
)
from src.core.platform.protocols import (
    ClipboardReader,
    HotkeyListener,
    PasteSender,
    ProcessInspector,
    SingleInstanceController,
    SoundPlayer,
    StartupController,
)
from src.core.platform.services import PlatformServices

__all__ = [
    "ClipboardReader",
    "HotkeyListener",
    "PasteSender",
    "PlatformError",
    "PlatformServices",
    "ProcessInspector",
    "SingleInstanceController",
    "SingleInstanceError",
    "SoundPlayer",
    "StartupController",
    "UnsupportedFeatureError",
]
