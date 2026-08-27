"""Clip Watcher固有のアプリケーション型インターフェース。"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any

from reusable_gui.core.bootstrap.base_application import ApplicationState
from reusable_gui.core.bootstrap.base_application import (
    BaseApplication as ReusableBaseApplication,
)

__all__ = ["ApplicationState", "BaseApplication"]

if TYPE_CHECKING:
    from src.core.clipboard.clipboard_monitor import ClipboardMonitor
    from src.core.config.settings_manager import SettingsManager
    from src.core.events.event_dispatcher import EventDispatcher
    from src.event_handlers.file_handlers import FileEventHandlers
    from src.event_handlers.history_handlers import HistoryEventHandlers
    from src.event_handlers.settings_handlers import SettingsEventHandlers
    from src.gui.icon_manager import IconManager
    from src.gui.main_gui import ClipWatcherGUI
    from src.gui.theme_manager import ThemeManager
    from src.plugins.manager import PluginManager
    from src.services.history_service import HistoryService
    from src.utils.i18n import Translator
    from src.utils.undo_manager import UndoManager


class BaseApplication(ReusableBaseApplication):
    """Clip Watcherが提供するサービスを型安全に公開する基底クラス。"""

    master: tk.Tk
    settings_manager: SettingsManager
    history_service: HistoryService
    monitor: ClipboardMonitor
    plugin_manager: PluginManager
    event_dispatcher: EventDispatcher
    theme_manager: ThemeManager
    icon_manager: IconManager | None
    translator: Translator
    undo_manager: UndoManager
    history_handlers: HistoryEventHandlers
    file_handlers: FileEventHandlers
    settings_handlers: SettingsEventHandlers
    gui: ClipWatcherGUI
    history_sort_ascending: bool
    always_on_top_var: tk.BooleanVar
    theme_var: tk.StringVar

    def get_pinned_hotkey_combo(self, history_id: int) -> str | None:
        """履歴項目に割り当てられたホットキーを返す。"""
        raise NotImplementedError

    def get_pinned_hotkey_bindings(self) -> dict[int, str]:
        """ピン留め履歴に割り当てられたホットキーのコピーを返す。"""
        raise NotImplementedError

    def open_pinned_hotkey_dialog(self, history_id: int) -> None:
        """履歴項目のホットキー設定ダイアログを開く。"""
        raise NotImplementedError

    def remove_pinned_hotkey_binding(self, history_id: int) -> bool:
        """履歴項目のホットキー割当を解除する。"""
        raise NotImplementedError

    def create_toplevel(
        self, toplevel_class: type[tk.Toplevel], *args: Any, **kwargs: Any
    ) -> Any:
        """アプリ固有の引数を注入してトップレベルウィンドウを生成する。"""
        raise NotImplementedError
