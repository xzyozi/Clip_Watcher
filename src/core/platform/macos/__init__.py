"""src/core/platform/macos/__init__.py

macOS 具象プラットフォームアダプター群。
"""

from src.core.platform.macos.clipboard_reader import MacOSClipboardReader
from src.core.platform.macos.hotkey import MacOSHotkeyListener
from src.core.platform.macos.paste_sender import MacOSPasteSender
from src.core.platform.macos.process_inspector import MacOSProcessInspector
from src.core.platform.macos.sound_player import MacOSSoundPlayer
from src.core.platform.macos.startup import MacOSStartupController
from src.core.platform.posix.single_instance import (
    PosixSingleInstanceController as MacOSSingleInstanceController,
)

__all__ = [
    "MacOSClipboardReader",
    "MacOSHotkeyListener",
    "MacOSProcessInspector",
    "MacOSSingleInstanceController",
    "MacOSSoundPlayer",
    "MacOSStartupController",
    "MacOSPasteSender",
]
