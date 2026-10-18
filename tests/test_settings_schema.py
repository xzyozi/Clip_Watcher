"""tests/test_settings_schema.py

SettingsManager と reusable_gui schema のスキーマ設定テスト。
"""

from unittest.mock import patch

from reusable_gui.core.config.schema import SettingField, WidgetType
from reusable_gui.core.config.settings_manager import BaseSettingsManager
from src.core.config.settings_manager import (
    SettingsManager,
    _get_hotkey_label,
    _get_startup_label,
)
from src.core.events.event_dispatcher import EventDispatcher
from src.utils.i18n import Translator


def test_widget_type_hotkey_capture_exists() -> None:
    assert hasattr(WidgetType, "HOTKEY_CAPTURE")
    assert WidgetType.HOTKEY_CAPTURE in WidgetType


def test_settings_manager_inherits_base_settings_manager() -> None:
    dispatcher = EventDispatcher()
    manager = SettingsManager(dispatcher)
    assert isinstance(manager, BaseSettingsManager)


def test_settings_manager_get_settings_schema() -> None:
    dispatcher = EventDispatcher()
    manager = SettingsManager(dispatcher)
    schema = manager.get_settings_schema()

    assert isinstance(schema, list)
    assert len(schema) > 0
    assert all(isinstance(f, SettingField) for f in schema)

    keys = [f.key for f in schema]
    assert "theme" in keys
    assert "language" in keys
    assert "always_on_top" in keys
    assert "startup_on_boot" in keys
    assert "global_hotkey_enabled" in keys
    assert "global_hotkey_combo" in keys

    hotkey_enabled_field = next(f for f in schema if f.key == "global_hotkey_enabled")
    assert hotkey_enabled_field.widget_type == WidgetType.CHECKBUTTON
    assert hotkey_enabled_field.tab == "General"

    hotkey_combo_field = next(f for f in schema if f.key == "global_hotkey_combo")
    assert hotkey_combo_field.widget_type == WidgetType.HOTKEY_CAPTURE
    assert hotkey_combo_field.tab == "General"


def test_copy_warning_setting_is_disabled_by_default() -> None:
    dispatcher = EventDispatcher()
    manager = SettingsManager(dispatcher)

    assert manager.get_setting("copy_warning_enabled") is False

    schema = manager.get_settings_schema()
    field = next(item for item in schema if item.key == "copy_warning_enabled")
    assert field.widget_type == WidgetType.CHECKBUTTON
    assert field.tab == "History"
    assert field.default is False


def test_os_specific_settings_labels() -> None:
    dispatcher = EventDispatcher()
    manager = SettingsManager(dispatcher)
    translator = Translator(manager)

    with patch("sys.platform", "darwin"):
        assert _get_startup_label() == "Start at Login"
        assert _get_hotkey_label() == "Enable Global Hotkey"

    with patch("sys.platform", "linux"):
        assert _get_startup_label() == "Start on System Boot"
        assert _get_hotkey_label() == "Enable Global Hotkey (Windows/macOS only)"

    with patch("sys.platform", "win32"):
        assert _get_startup_label() == "Start with Windows"
        assert _get_hotkey_label() == "Enable Global Hotkey"

    # 日本語翻訳の検証
    translator.current_lang = "ja"
    assert translator.translate("Start with Windows") == "Windows 起動時に自動起動"
    assert translator.translate("Start at Login") == "ログイン時に自動起動"
    assert translator.translate("Start on System Boot") == "システム起動時に自動起動"
    assert (
        translator.translate("Enable Global Hotkey (Windows/macOS only)")
        == "グローバルホットキーを有効にする (Windows/macOS限定)"
    )
    assert (
        translator.translate("Enable Global Hotkey (Windows only)")
        == "グローバルホットキーを有効にする (Windows限定)"
    )
