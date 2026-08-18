"""tests/test_settings_schema.py

SettingsManager と reusable_gui schema のスキーマ設定テスト。
"""
from reusable_gui.core.config.schema import SettingField, WidgetType
from reusable_gui.core.config.settings_manager import BaseSettingsManager
from src.core.config.settings_manager import SettingsManager
from src.core.events.event_dispatcher import EventDispatcher


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
