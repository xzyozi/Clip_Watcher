"""src/core/platform/posix/__init__.py

POSIX (macOS / Linux) 共通の具象プラットフォームアダプター群。
"""

from src.core.platform.posix.single_instance import PosixSingleInstanceController

__all__ = [
    "PosixSingleInstanceController",
]
