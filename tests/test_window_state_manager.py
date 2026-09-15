"""tests/test_window_state_manager.py

WindowStateManager の状態遷移と Strategy 実行の検証テスト。
"""

import tkinter as tk
from unittest.mock import MagicMock

from src.core.window.window_state_manager import (
    MinimizedStrategy,
    VisibleStrategy,
    WindowState,
    WindowStateManager,
)


def test_window_state_manager_initial_state(tk_root: tk.Tk) -> None:
    manager = WindowStateManager(tk_root)
    assert manager.state == WindowState.VISIBLE


def test_window_state_manager_transitions(tk_root: tk.Tk) -> None:
    manager = WindowStateManager(tk_root)

    mock_visible = MagicMock()
    mock_minimized = MagicMock()

    manager.register_strategy(WindowState.VISIBLE, mock_visible)
    manager.register_strategy(WindowState.MINIMIZED, mock_minimized)

    # minimize
    manager.minimize()
    assert manager.state == WindowState.MINIMIZED
    mock_minimized.enter.assert_called_once_with(tk_root)

    # toggle -> visible
    manager.toggle()
    assert manager.state == WindowState.VISIBLE
    mock_visible.enter.assert_called_once_with(tk_root)

    # toggle -> minimized
    manager.toggle()
    assert manager.state == WindowState.MINIMIZED

    # show -> visible
    manager.show()
    assert manager.state == WindowState.VISIBLE


def test_strategies_execution(tk_root: tk.Tk) -> None:
    visible_strat = VisibleStrategy()
    minimized_strat = MinimizedStrategy()

    visible_strat.enter(tk_root)
    minimized_strat.enter(tk_root)
