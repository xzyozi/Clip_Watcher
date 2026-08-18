from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from reusable_gui.core.config.schema import SettingField
from reusable_gui.windows.settings_window import SettingsWindow as ReusableSettingsWindow
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
        if hasattr(self.app_instance, "plugin_manager") and self.app_instance.plugin_manager:
            provider = PluginSettingsSchemaProvider(self.app_instance.plugin_manager)
            plugin_schema = provider.get_fields()
        return [*core_schema, *plugin_schema]

    def _validate_pending_values(self) -> bool:
        enabled_var = self._vars.get("global_hotkey_enabled")
        combo_var = self._vars.get("global_hotkey_combo")

        if enabled_var is not None and combo_var is not None:
            enabled = bool(enabled_var.get())
            combo = str(combo_var.get())

            hrm = getattr(self.app_instance, "hotkey_registration_manager", None)
            if hrm is not None:
                success = hrm.reconfigure(enabled, combo)
                if not success:
                    from tkinter import messagebox

                    messagebox.showerror(
                        "Hotkey Error",
                        f"Failed to register global hotkey: {combo!r}. The key may be in use by another application.",
                        parent=self,
                    )
                    return False
        return True
