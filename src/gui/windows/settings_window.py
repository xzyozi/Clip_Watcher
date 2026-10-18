from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from reusable_gui.core.config.schema import SettingField
from reusable_gui.windows.settings_window import (
    SettingsWindow as ReusableSettingsWindow,
)
from src.plugins.settings_schema_provider import PluginSettingsSchemaProvider

if TYPE_CHECKING:
    import tkinter as tk

    from src.core.bootstrap.base_application import BaseApplication
    from src.core.config.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class SettingsWindow(ReusableSettingsWindow):
    """Clip Watcher 専用のスキーマ駆動設定ウィンドウ。

    reusable_gui の SettingsWindow を継承し、コア設定スキーマと
    PluginSettingsSchemaProvider の動的スキーマを合成する。
    また、保存/適用前の検証フック (_validate_pending_values) で
    ホットキー登録の整合性検証および更新を実施する。
    """

    def __init__(
        self,
        master: tk.Misc,
        app_instance: BaseApplication,
        settings_manager: SettingsManager,
    ) -> None:
        super().__init__(master, app_instance, settings_manager)

    def _get_schema(self) -> list[SettingField]:
        core_schema = self.settings_manager.get_settings_schema()
        plugin_schema: list[SettingField] = []
        if (
            hasattr(self.app_instance, "plugin_manager")
            and self.app_instance.plugin_manager
        ):
            provider = PluginSettingsSchemaProvider(self.app_instance.plugin_manager)
            plugin_schema = provider.get_fields()
        return [*core_schema, *plugin_schema]

    def _validate_pending_values(self) -> bool:
        enabled_var = self._vars.get("global_hotkey_enabled")
        combo_var = self._vars.get("global_hotkey_combo")

        if enabled_var is not None and combo_var is not None:
            enabled = bool(enabled_var.get())
            combo = str(combo_var.get()).strip()

            if enabled:
                hrm = getattr(self.app_instance, "hotkey_registration_manager", None)
                if hrm is None:
                    from tkinter import messagebox

                    messagebox.showerror(
                        self._tr("Hotkey Error"),
                        self._tr("Global hotkey is not supported on this platform."),
                        parent=self,
                    )
                    return False

                from src.core.hotkey.global_hotkey_listener import parse_hotkey_string

                try:
                    parse_hotkey_string(combo)
                except ValueError as e:
                    from tkinter import messagebox

                    msg_tmpl = self._tr("Invalid hotkey format: {combo}. ({error})")
                    msg = (
                        msg_tmpl.format(combo=repr(combo), error=e)
                        if "{combo}" in msg_tmpl
                        else f"Invalid hotkey format: {combo!r}. ({e})"
                    )
                    messagebox.showerror(
                        self._tr("Hotkey Error"),
                        msg,
                        parent=self,
                    )
                    return False
        return True
