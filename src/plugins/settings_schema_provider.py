from __future__ import annotations

from typing import TYPE_CHECKING

from reusable_gui.core.config.schema import SettingField, WidgetType

if TYPE_CHECKING:
    from src.plugins.manager import PluginManager


class PluginSettingsSchemaProvider:
    """PluginManager から GUI プラグインを取得し、
    Modules タブの表示切替用 SettingField スキーマを動的に生成するクラス。
    """

    def __init__(self, plugin_manager: PluginManager) -> None:
        self._plugin_manager = plugin_manager

    def get_fields(self) -> list[SettingField]:
        fields: list[SettingField] = []
        for plugin in self._plugin_manager.get_gui_plugins():
            setting_key = f"show_{plugin.name.lower().replace(' ', '_')}_tab"
            fields.append(
                SettingField(
                    key=setting_key,
                    label=f"Show {plugin.name} Tab",
                    widget_type=WidgetType.CHECKBUTTON,
                    tab="Modules",
                    group="Main Window Tabs",
                    default=True,
                )
            )
        return fields
