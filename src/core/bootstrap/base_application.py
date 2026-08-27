"""Clip Watcher固有のアプリケーション型インターフェース。"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from reusable_gui.core.bootstrap.base_application import (
    ApplicationState,
    BaseApplication as ReusableBaseApplication,
)

if TYPE_CHECKING:
    from src.core.clipboard.clipboard_monitor import ClipboardMonitor
    from src.core.config.settings_manager import SettingsManager
    from src.core.events.event_dispatcher import EventDispatcher
    from src.event_handlers.history_handlers import HistoryEventHandlers
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
    gui: ClipWatcherGUI
