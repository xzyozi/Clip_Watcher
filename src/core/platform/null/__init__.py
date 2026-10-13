"""src/core/platform/null/__init__.py

ホットキー用の暫定 Null（安全なダミー）アダプター。

ホットキーは Windows 限定のため、非 Windows ではこの Null 実装で起動を継続する。
他 OS 対応と本パッケージの廃止は #150 で扱う。
"""

from src.core.platform.null.hotkey_listener import NullHotkeyListener

__all__ = ["NullHotkeyListener"]
