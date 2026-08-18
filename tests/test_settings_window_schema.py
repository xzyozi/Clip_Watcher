"""tests/test_settings_window_schema.py

reusable_gui 継承版の SettingsWindow スキーマ駆動テスト。
"""
import tkinter as tk
from unittest.mock import MagicMock

from reusable_gui.core.config.schema import WidgetType
from reusable_gui.windows.settings_window import SettingsWindow as ReusableSettingsWindow
from src.core.config.settings_manager import SettingsManager
from src.core.events.event_dispatcher import EventDispatcher
from src.gui.windows.settings_window import SettingsWindow


def test_settings_window_inherits_reusable_settings_window() -> None:
    assert issubclass(SettingsWindow, ReusableSettingsWindow)


def test_settings_window_schema_composition() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        dispatcher = EventDispatcher()
        settings_manager = SettingsManager(dispatcher)

        app_mock = MagicMock()
        app_mock.plugin_manager.get_gui_plugins.return_value = []

        window = SettingsWindow(root, app_mock, settings_manager)
        schema = window._get_schema()

        keys = [f.key for f in schema]
        assert "theme" in keys
        assert "global_hotkey_enabled" in keys
        assert "global_hotkey_combo" in keys

        hotkey_combo_field = next(f for f in schema if f.key == "global_hotkey_combo")
        assert hotkey_combo_field.widget_type == WidgetType.HOTKEY_CAPTURE

        window.destroy()
    finally:
        root.destroy()
