"""src/core/window

ウィンドウ状態の管理・状態遷移 Strategy パッケージ。
"""

from src.core.window.window_state_manager import (
    MinimizedStrategy,
    VisibleStrategy,
    WindowState,
    WindowStateManager,
    WindowStateStrategy,
)

__all__ = [
    "MinimizedStrategy",
    "VisibleStrategy",
    "WindowState",
    "WindowStateManager",
    "WindowStateStrategy",
]
