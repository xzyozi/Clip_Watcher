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


def test_settings_window_initializes_with_japanese_translations(
    tk_root: tk.Tk,
) -> None:
    """言語が ja の場合、タイトル・タブ・ボタン等が日本語で初期化されること。"""
    from src.utils.i18n import Translator

    dispatcher = EventDispatcher()
    settings_manager = SettingsManager(dispatcher)
    settings_manager.set_setting("language", "ja")
    translator = Translator(settings_manager)

    app_mock = MagicMock()
    app_mock.translator = translator
    app_mock.event_dispatcher = dispatcher
    app_mock.plugin_manager.get_gui_plugins.return_value = []

    window = SettingsWindow(tk_root, app_mock, settings_manager)

    assert window.title() == "設定"
    tab_texts = [
        window.notebook.tab(i, "text") for i in range(window.notebook.index("end"))
    ]
    assert "一般" in tab_texts
    assert "履歴" in tab_texts
    assert "通知" in tab_texts

    # ボタンの日本語確認
    button_texts = [
        w.cget("text")
        for w, kind, _ in window._translatable_widgets
        if kind == "text" and isinstance(w, tk.Widget)
    ]
    assert "保存" in button_texts
    assert "キャンセル" in button_texts
    assert "適用" in button_texts
    assert "追加" in button_texts
    assert "削除" in button_texts

    window.destroy()


def test_settings_window_updates_dynamically_on_language_change(
    tk_root: tk.Tk,
) -> None:
    """LANGUAGE_CHANGED イベントを受信した際に、開いている設定画面のタイトル・タブ・ボタンが動的に更新されること。"""
    from src.utils.i18n import Translator

    dispatcher = EventDispatcher()
    settings_manager = SettingsManager(dispatcher)
    settings_manager.set_setting("language", "en")
    translator = Translator(settings_manager)

    app_mock = MagicMock()
    app_mock.translator = translator
    app_mock.event_dispatcher = dispatcher
    app_mock.plugin_manager.get_gui_plugins.return_value = []

    window = SettingsWindow(tk_root, app_mock, settings_manager)

    assert window.title() == "Settings"
    initial_tabs = [
        window.notebook.tab(i, "text") for i in range(window.notebook.index("end"))
    ]
    assert "General" in initial_tabs

    # 設定画面内で言語を ja に変更して Apply を実行
    window._vars["language"].set("ja")
    window._apply_only()

    # Apply 後、即座に日本語へ動的更新されていること
    assert window.title() == "設定"
    updated_tabs = [
        window.notebook.tab(i, "text") for i in range(window.notebook.index("end"))
    ]
    assert "一般" in updated_tabs
    assert "履歴" in updated_tabs

    window.destroy()
