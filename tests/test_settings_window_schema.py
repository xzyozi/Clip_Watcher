"""tests/test_settings_window_schema.py

reusable_gui 継承版の SettingsWindow スキーマ駆動テスト。
"""

import tkinter as tk
from unittest.mock import MagicMock

from reusable_gui.core.config.schema import WidgetType
from reusable_gui.windows.settings_window import (
    SettingsWindow as ReusableSettingsWindow,
)
from src.core.config.settings_manager import SettingsManager
from src.core.events.event_dispatcher import EventDispatcher
from src.gui.windows.settings_window import SettingsWindow


def test_settings_window_inherits_reusable_settings_window() -> None:
    assert issubclass(SettingsWindow, ReusableSettingsWindow)


def test_settings_window_schema_composition(tk_root: tk.Tk) -> None:
    dispatcher = EventDispatcher()
    settings_manager = SettingsManager(dispatcher)

    app_mock = MagicMock()
    app_mock.plugin_manager.get_gui_plugins.return_value = []

    window = SettingsWindow(tk_root, app_mock, settings_manager)
    schema = window._get_schema()

    keys = [f.key for f in schema]
    assert "theme" in keys
    assert "global_hotkey_enabled" in keys
    assert "global_hotkey_combo" in keys

    hotkey_combo_field = next(f for f in schema if f.key == "global_hotkey_combo")
    assert hotkey_combo_field.widget_type == WidgetType.HOTKEY_CAPTURE

    window.destroy()


def test_settings_window_with_translator_instance(tk_root: tk.Tk) -> None:
    from src.utils.i18n import Translator

    dispatcher = EventDispatcher()
    settings_manager = SettingsManager(dispatcher)
    translator = Translator(settings_manager)

    app_mock = MagicMock()
    app_mock.translator = translator
    app_mock.plugin_manager.get_gui_plugins.return_value = []

    window = SettingsWindow(tk_root, app_mock, settings_manager)
    assert window.winfo_exists()
    window.destroy()
