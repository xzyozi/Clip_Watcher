"""tests/test_settings_window_schema.py

reusable_gui 継承版の SettingsWindow スキーマ駆動テスト。
"""

import tkinter as tk
from unittest.mock import MagicMock, patch

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


def test_validate_pending_values_rejects_when_hotkey_not_supported(
    tk_root: tk.Tk,
) -> None:
    dispatcher = EventDispatcher()
    settings_manager = SettingsManager(dispatcher)
    app_mock = MagicMock()
    app_mock.hotkey_registration_manager = None

    window = SettingsWindow(tk_root, app_mock, settings_manager)
    window._vars["global_hotkey_enabled"] = tk.BooleanVar(value=True)
    window._vars["global_hotkey_combo"] = tk.StringVar(value="Ctrl+Shift+V")

    with patch("tkinter.messagebox.showerror") as mock_err:
        assert window._validate_pending_values() is False
        mock_err.assert_called_once()
    window.destroy()


def test_validate_pending_values_rejects_invalid_syntax(tk_root: tk.Tk) -> None:
    dispatcher = EventDispatcher()
    settings_manager = SettingsManager(dispatcher)
    app_mock = MagicMock()
    app_mock.hotkey_registration_manager = MagicMock()

    window = SettingsWindow(tk_root, app_mock, settings_manager)
    window._vars["global_hotkey_enabled"] = tk.BooleanVar(value=True)
    window._vars["global_hotkey_combo"] = tk.StringVar(value="InvalidKeyName+++")

    with patch("tkinter.messagebox.showerror") as mock_err:
        assert window._validate_pending_values() is False
        mock_err.assert_called_once()
    window.destroy()


def test_validate_pending_values_does_not_call_reconfigure(tk_root: tk.Tk) -> None:
    dispatcher = EventDispatcher()
    settings_manager = SettingsManager(dispatcher)
    mock_hrm = MagicMock()
    app_mock = MagicMock()
    app_mock.hotkey_registration_manager = mock_hrm

    window = SettingsWindow(tk_root, app_mock, settings_manager)
    window._vars["global_hotkey_enabled"] = tk.BooleanVar(value=True)
    window._vars["global_hotkey_combo"] = tk.StringVar(value="Ctrl+Shift+V")

    assert window._validate_pending_values() is True
    # #141: バリデーションフェーズでは reconfigure の副作用を起こさないこと
    mock_hrm.reconfigure.assert_not_called()
    window.destroy()
