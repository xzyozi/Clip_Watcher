"""src/core/hotkey

グローバルホットキーの検知・登録状態管理パッケージ。
"""

from src.core.hotkey.global_hotkey_listener import (
    GlobalHotkeyListener,
    format_hotkey,
    parse_hotkey_string,
)
from src.core.hotkey.hotkey_registration_manager import HotkeyRegistrationManager

__all__ = [
    "GlobalHotkeyListener",
    "HotkeyRegistrationManager",
    "format_hotkey",
    "parse_hotkey_string",
]
