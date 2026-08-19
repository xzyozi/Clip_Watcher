from __future__ import annotations

import logging
import tkinter as tk
from enum import Enum, auto
from typing import Protocol

logger = logging.getLogger(__name__)


class WindowState(Enum):
    VISIBLE = auto()
    MINIMIZED = auto()
    # 将来追加: HIDDEN_TO_TRAY = auto()


class WindowStateStrategy(Protocol):
    def enter(self, root: tk.Tk) -> None: ...


class VisibleStrategy:
    def enter(self, root: tk.Tk) -> None:
        root.deiconify()
        root.lift()
        root.focus_force()


class MinimizedStrategy:
    def enter(self, root: tk.Tk) -> None:
        root.iconify()


class WindowStateManager:
    """ウィンドウの表示状態と遷移を一元管理するマネージャ。

    <Map> / <Unmap> イベントを購読し、OSの最小化・復元操作にも追従する。
    """

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._state = WindowState.VISIBLE
        self._strategies: dict[WindowState, WindowStateStrategy] = {
            WindowState.VISIBLE: VisibleStrategy(),
            WindowState.MINIMIZED: MinimizedStrategy(),
        }
        root.bind("<Unmap>", self._on_unmap, add="+")
        root.bind("<Map>", self._on_map, add="+")

    @property
    def state(self) -> WindowState:
        return self._state

    def show(self) -> None:
        self._transition_to(WindowState.VISIBLE)

    def minimize(self) -> None:
        self._transition_to(WindowState.MINIMIZED)

    def toggle(self) -> None:
        if self._state == WindowState.VISIBLE:
            self.minimize()
        else:
            self.show()

    def register_strategy(self, state: WindowState, strategy: WindowStateStrategy) -> None:
        self._strategies[state] = strategy

    def _transition_to(self, new_state: WindowState) -> None:
        strategy = self._strategies.get(new_state)
        if strategy is None:
            logger.warning("未知のウィンドウ状態への遷移が要求されました: %s", new_state)
            return
        strategy.enter(self._root)
        self._state = new_state

    def _on_unmap(self, event: tk.Event) -> None:
        if event.widget == self._root:
            self._state = WindowState.MINIMIZED

    def _on_map(self, event: tk.Event) -> None:
        if event.widget == self._root:
            self._state = WindowState.VISIBLE
