"""src/core/platform/windows/__init__.py

Windows 具象プラットフォームアダプター群。
"""

from src.core.hotkey.global_hotkey_listener import (
    GlobalHotkeyListener as WindowsHotkeyListener,
)
from src.core.platform.windows.clipboard_reader import WindowsClipboardReader
from src.core.platform.windows.paste_sender import WindowsPasteSender
from src.core.platform.windows.process_inspector import WindowsProcessInspector
from src.core.platform.windows.single_instance import WindowsSingleInstanceController
from src.core.platform.windows.sound_player import WindowsSoundPlayer
from src.core.platform.windows.startup import WindowsStartupController

__all__ = [
    "WindowsClipboardReader",
    "WindowsProcessInspector",
    "WindowsSingleInstanceController",
    "WindowsSoundPlayer",
    "WindowsStartupController",
    "WindowsPasteSender",
    "WindowsHotkeyListener",
]
