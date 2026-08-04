import json
import logging
import os
from typing import Any

from src.core.events.event_dispatcher import EventDispatcher
from reusable_gui.core.config.schema import SettingField, WidgetType

from . import defaults

logger = logging.getLogger(__name__)


class SettingsManager:
    def __init__(self, event_dispatcher: EventDispatcher, file_path: str = "settings.json") -> None:
        self.event_dispatcher = event_dispatcher
        self.file_path = file_path
        self.settings: dict[str, Any] = self._get_default_settings()

    def load_and_notify(self) -> None:
        """Loads settings from the file and notifies listeners."""
        loaded_settings = self._load_settings()
        self.settings.update(loaded_settings)
        self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)

    def _read_settings_file(self, filepath: str) -> dict[str, Any] | None:
        """Reads a JSON settings object, returning None for invalid input."""
        try:
            with open(filepath, encoding="utf-8") as f:
                loaded_settings = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            logger.warning("Could not read settings file %s: %s", filepath, error)
            return None

        if not isinstance(loaded_settings, dict):
            logger.warning("Settings file %s must contain a JSON object.", filepath)
            return None
        return loaded_settings

    def _is_valid_known_setting(self, key: str, value: Any) -> bool:
        """Validates the type and bounds of built-in settings."""
        if key == "theme":
            return isinstance(value, str) and value in defaults.THEMES
        if key == "history_limit":
            return (
                type(value) is int
                and defaults.HISTORY_LIMIT_MIN <= value <= defaults.HISTORY_LIMIT_MAX
            )
        if key in {"clipboard_content_font_size", "history_font_size"}:
            return type(value) is int and value > 0
        if key == "excluded_apps":
            return isinstance(value, list) and all(isinstance(app, str) for app in value)

        default_value = defaults.DEFAULT_USER_SETTINGS[key]
        if isinstance(default_value, bool):
            return isinstance(value, bool)
        if isinstance(default_value, int):
            return type(value) is int
        if isinstance(default_value, str):
            return isinstance(value, str)
        if isinstance(default_value, list):
            return isinstance(value, list)
        return type(value) is type(default_value)

    def _validate_settings(
        self, loaded_settings: dict[str, Any], *, reject_invalid: bool
    ) -> dict[str, Any] | None:
        """Keeps valid settings and optionally rejects an invalid import as a whole."""
        validated_settings: dict[str, Any] = {}
        invalid_keys: list[str] = []

        for key, value in loaded_settings.items():
            if key not in defaults.DEFAULT_USER_SETTINGS:
                # Keep extension settings owned by plugins or newer application versions.
                validated_settings[key] = value
            elif self._is_valid_known_setting(key, value):
                validated_settings[key] = value
            else:
                invalid_keys.append(key)

        if invalid_keys:
            logger.warning("Ignoring invalid settings: %s", ", ".join(invalid_keys))
            if reject_invalid:
                return None

        return validated_settings

    def _load_settings(self) -> dict[str, Any]:
        if not os.path.exists(self.file_path):
            return {}

        loaded_settings = self._read_settings_file(self.file_path)
        if loaded_settings is None:
            return {}

        validated_settings = self._validate_settings(loaded_settings, reject_invalid=False)
        return validated_settings if validated_settings is not None else {}

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
        if not os.path.exists(filepath):
            return False

        loaded_settings = self._read_settings_file(filepath)
        if loaded_settings is None:
            return False

        validated_settings = self._validate_settings(loaded_settings, reject_invalid=True)
        if validated_settings is None:
            return False

        if "theme" in validated_settings and "history_limit" in validated_settings:
            self.settings.update(validated_settings)
            self.event_dispatcher.dispatch("SETTINGS_CHANGED", self.settings)
            return True
        return False

    def get_settings_schema(self) -> list[SettingField]:
        """Clip Watcher の設定項目スキーマを返す。

        タブ・グループ・ウィジェット種別を定義することで、
        SettingsWindow が UI を動的に生成できる。
        """
        d = defaults

        return [
            # ── General / Appearance ─────────────────────────────────────────
            SettingField(
                key="theme", label="Theme",
                widget_type=WidgetType.OPTION_MENU,
                tab="General", group="Appearance",
                default="light", choices=["light", "dark"],
            ),
            SettingField(
                key="language", label="Language",
                widget_type=WidgetType.OPTION_MENU,
                tab="General", group="Appearance",
                default="en", choices=["en", "ja"],
            ),

            # ── General / Window Behavior ────────────────────────────────────
            SettingField(
                key="always_on_top", label="Always on Top",
                widget_type=WidgetType.CHECKBUTTON,
                tab="General", group="Window Behavior",
                default=False,
            ),

            # ── General / Startup ────────────────────────────────────────────
            SettingField(
                key="startup_on_boot", label="Start with Windows",
                widget_type=WidgetType.CHECKBUTTON,
                tab="General", group="Startup",
                default=False,
            ),

            # ── History ──────────────────────────────────────────────────────
            SettingField(
                key="history_limit", label="History Limit",
                widget_type=WidgetType.SPINBOX,
                tab="History", group="History Options",
                default=50,
                min_value=d.HISTORY_LIMIT_MIN,
                max_value=d.HISTORY_LIMIT_MAX,
                increment=d.HISTORY_LIMIT_INCREMENT,
                width=10,
            ),

            # ── Notifications / Behavior ─────────────────────────────────────
            SettingField(
                key="notifications_enabled", label="Enable Notifications",
                widget_type=WidgetType.CHECKBUTTON,
                tab="Notifications", group="Notification Behavior",
                default=True,
            ),
            SettingField(
                key="notification_show_app_name", label="Show App Name in Notification",
                widget_type=WidgetType.CHECKBUTTON,
                tab="Notifications", group="Notification Behavior",
                default=True,
            ),
            SettingField(
                key="notification_sound_enabled", label="Enable Notification Sound",
                widget_type=WidgetType.CHECKBUTTON,
                tab="Notifications", group="Notification Behavior",
                default=False,
            ),

            # ── Notifications / Content ──────────────────────────────────────
            SettingField(
                key="notification_content_length", label="Notification Content Length",
                widget_type=WidgetType.SPINBOX,
                tab="Notifications", group="Notification Content",
                default=50, min_value=10, max_value=200, increment=10, width=10,
            ),

            # ── Font / Clipboard Content ──────────────────────────────────────
            SettingField(
                key="clipboard_content_font_family", label="Clipboard Content Font",
                widget_type=WidgetType.FONT_PICKER,
                tab="Font", group="Clipboard Content Font",
                default="TkDefaultFont",
            ),
            SettingField(
                key="clipboard_content_font_size", label="Size",
                widget_type=WidgetType.SPINBOX,
                tab="Font", group="Clipboard Content Font",
                default=10, min_value=8, max_value=24, increment=1, width=5,
            ),

            # ── Font / History ────────────────────────────────────────────────
            SettingField(
                key="history_font_family", label="History Font",
                widget_type=WidgetType.FONT_PICKER,
                tab="Font", group="History Font",
                default="TkDefaultFont",
            ),
            SettingField(
                key="history_font_size", label="Size",
                widget_type=WidgetType.SPINBOX,
                tab="Font", group="History Font",
                default=10, min_value=8, max_value=24, increment=1, width=5,
            ),

            # ── Excluded Apps ─────────────────────────────────────────────────
            SettingField(
                key="excluded_apps", label="Excluded Applications",
                widget_type=WidgetType.LISTBOX_EDIT,
                tab="Excluded Apps", group="",
                default=[],
            ),
        ]
