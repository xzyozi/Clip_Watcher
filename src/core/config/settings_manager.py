import json
import os
from typing import Any, cast

from reusable_gui.core.config.schema import SettingField, WidgetType
from reusable_gui.core.config.settings_manager import BaseSettingsManager
from src.core.events.event_dispatcher import EventDispatcher

from . import defaults


class SettingsManager(BaseSettingsManager):
    def __init__(
        self, event_dispatcher: EventDispatcher, file_path: str = "settings.json"
    ) -> None:
        self.event_dispatcher = event_dispatcher
        self.file_path = file_path
        self._settings: dict[str, Any] = self._get_default_settings()

    @property
    def settings(self) -> dict[str, Any]:
        return self._settings

    @settings.setter
    def settings(self, val: dict[str, Any]) -> None:
        self._settings = val

    def load_and_notify(self) -> None:
        """Loads settings from the file and notifies listeners."""
        loaded_settings = self._load_settings()
        self.settings.update(loaded_settings)
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def _load_settings(self) -> dict[str, Any]:
        if os.path.exists(self.file_path):
            with open(self.file_path, encoding="utf-8") as f:
                try:
                    return cast(dict[str, Any], json.load(f))
                except json.JSONDecodeError:
                    return {}
        return {}

    def _get_default_settings(self) -> dict[str, Any]:
        return defaults.DEFAULT_USER_SETTINGS.copy()

    def save_settings(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)
        # Notify listeners that settings have changed
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value

    def notify_listeners(self) -> None:
        """Notifies listeners about the current settings."""
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def save_settings_to_file(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)

    def load_settings_from_file(self, filepath: str) -> bool:
        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8") as f:
                try:
                    loaded_settings = json.load(f)
                    if (
                        "theme" in loaded_settings
                        and "history_limit" in loaded_settings
                    ):
                        self.settings.update(loaded_settings)
                        self.event_dispatcher.dispatch(
                            "SETTINGS_CHANGED", self.settings
                        )
                        return True
                except (json.JSONDecodeError, TypeError):
                    return False
        return False

    def get_settings_schema(self) -> list[SettingField]:
        """Clip Watcher の設定項目スキーマを返す。

        タブ・グループ・ウィジェット種別を定義することで
        SettingsWindow がUIを動的に生成する。
        """
        d = defaults

        return [
            # ── General / Appearance ───────────────────────────────────
            SettingField(
                key="theme",
                label="Theme",
                widget_type=WidgetType.OPTION_MENU,
                tab="General",
                group="Appearance",
                default="light",
                choices=["light", "dark"],
            ),
            SettingField(
                key="language",
                label="Language",
                widget_type=WidgetType.OPTION_MENU,
                tab="General",
                group="Appearance",
                default="en",
                choices=["en", "ja"],
            ),
            # ── General / Window Behavior ──────────────────────────────
            SettingField(
                key="always_on_top",
                label="Always on Top",
                widget_type=WidgetType.CHECKBUTTON,
                tab="General",
                group="Window Behavior",
                default=False,
            ),
            # ── General / Startup ──────────────────────────────────────
            SettingField(
                key="startup_on_boot",
                label="Start with Windows",
                widget_type=WidgetType.CHECKBUTTON,
                tab="General",
                group="Startup",
                default=False,
            ),
            # ── General / Global Hotkey ────────────────────────────────
            SettingField(
                key="global_hotkey_enabled",
                label="Enable Global Hotkey",
                widget_type=WidgetType.CHECKBUTTON,
                tab="General",
                group="Global Hotkey",
                default=True,
            ),
            SettingField(
                key="global_hotkey_combo",
                label="Show/Hide Hotkey",
                widget_type=WidgetType.HOTKEY_CAPTURE,
                tab="General",
                group="Global Hotkey",
                default="Ctrl+Shift+F",
            ),
            # ── History ───────────────────────────────────────────────
            SettingField(
                key="history_limit",
                label="History Limit",
                widget_type=WidgetType.SPINBOX,
                tab="History",
                group="History Options",
                default=d.DEFAULT_USER_SETTINGS["history_limit"],
                min_value=d.HISTORY_LIMIT_MIN,
                max_value=d.HISTORY_LIMIT_MAX,
                increment=d.HISTORY_LIMIT_INCREMENT,
                width=10,
            ),
            # ── Notifications / Behavior ───────────────────────────────
            SettingField(
                key="notifications_enabled",
                label="Enable Notifications",
                widget_type=WidgetType.CHECKBUTTON,
                tab="Notifications",
                group="Notification Behavior",
                default=True,
            ),
            SettingField(
                key="notification_show_app_name",
                label="Show App Name in Notification",
                widget_type=WidgetType.CHECKBUTTON,
                tab="Notifications",
                group="Notification Behavior",
                default=True,
            ),
            SettingField(
                key="notification_sound_enabled",
                label="Enable Notification Sound",
                widget_type=WidgetType.CHECKBUTTON,
                tab="Notifications",
                group="Notification Behavior",
                default=False,
            ),
            # ── Notifications / Content ────────────────────────────────
            SettingField(
                key="notification_content_length",
                label="Notification Content Length",
                widget_type=WidgetType.SPINBOX,
                tab="Notifications",
                group="Notification Content",
                default=50,
                min_value=10,
                max_value=200,
                increment=10,
                width=10,
            ),
            # ── Font / Clipboard Content ───────────────────────────────
            SettingField(
                key="clipboard_content_font_family",
                label="Clipboard Content Font",
                widget_type=WidgetType.FONT_PICKER,
                tab="Font",
                group="Clipboard Content Font",
                default="TkDefaultFont",
            ),
            SettingField(
                key="clipboard_content_font_size",
                label="Size",
                widget_type=WidgetType.SPINBOX,
                tab="Font",
                group="Clipboard Content Font",
                default=10,
                min_value=8,
                max_value=24,
                increment=1,
                width=5,
            ),
            # ── Font / History ─────────────────────────────────────────
            SettingField(
                key="history_font_family",
                label="History Font",
                widget_type=WidgetType.FONT_PICKER,
                tab="Font",
                group="History Font",
                default="TkDefaultFont",
            ),
            SettingField(
                key="history_font_size",
                label="Size",
                widget_type=WidgetType.SPINBOX,
                tab="Font",
                group="History Font",
                default=10,
                min_value=8,
                max_value=24,
                increment=1,
                width=5,
            ),
            # ── Excluded Apps ──────────────────────────────────────────
            SettingField(
                key="excluded_apps",
                label="Excluded Applications",
                widget_type=WidgetType.LISTBOX_EDIT,
                tab="Excluded Apps",
                group="",
                default=[],
            ),
        ]
