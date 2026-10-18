"""src/core/platform/linux/__init__.py

Linux 具象プラットフォームアダプター群。
"""

from src.core.platform.linux.process_inspector import LinuxProcessInspector

__all__ = [
    "LinuxProcessInspector",
]
