"""src/core/platform/macos/__init__.py

macOS 具象プラットフォームアダプター群。
"""

from src.core.platform.macos.clipboard_reader import MacOSClipboardReader
from src.core.platform.macos.process_inspector import MacOSProcessInspector

__all__ = [
    "MacOSClipboardReader",
    "MacOSProcessInspector",
]
