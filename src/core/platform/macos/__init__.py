"""src/core/platform/macos/__init__.py

macOS 具象プラットフォームアダプター群。
"""

from src.core.platform.macos.clipboard_reader import MacOSClipboardReader

__all__ = [
    "MacOSClipboardReader",
]
