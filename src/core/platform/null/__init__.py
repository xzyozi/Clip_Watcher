"""src/core/platform/null/__init__.py

非 Windows / ヘッドレス環境向けの Null（安全なダミー）プラットフォームアダプター群。
"""

from src.core.platform.null.hotkey_listener import NullHotkeyListener
from src.core.platform.null.paste_sender import NullPasteSender
from src.core.platform.null.process_inspector import NullProcessInspector
from src.core.platform.null.single_instance import NullSingleInstanceController
from src.core.platform.null.sound_player import NullSoundPlayer

__all__ = [
    "NullProcessInspector",
    "NullSingleInstanceController",
    "NullSoundPlayer",
    "NullPasteSender",
    "NullHotkeyListener",
]
