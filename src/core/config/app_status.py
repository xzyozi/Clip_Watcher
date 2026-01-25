from dataclasses import dataclass, field
from typing import Any

from src.core.dependency_checker import DependencyStatus


@dataclass
class AppStatus:
    """
    アプリケーションの全体的なランタイムステータスを保持します。
    """
    dependencies: DependencyStatus = field(default_factory=DependencyStatus)
    other_status: dict[str, Any] = field(default_factory=dict)

    def is_win32_available(self) -> bool:
        """win32関連の機能が利用可能かどうかを返します。"""
        return self.dependencies.win32_available
