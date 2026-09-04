"""tests/test_plugin_settings_schema.py

PluginSettingsSchemaProvider の動作検証テスト。
"""

from typing import Any

from reusable_gui.core.config.schema import WidgetType
from src.plugins.base_plugin import Plugin
from src.plugins.gui_plugin import GuiPlugin
from src.plugins.manager import PluginManager
from src.plugins.settings_schema_provider import PluginSettingsSchemaProvider


class DummyGuiPlugin(GuiPlugin):
    name = "Dummy Calendar"
    description = "Dummy Description"

    def create_gui_component(self, parent: Any, app_instance: Any) -> None:
        return None


class DummyNonGuiPlugin(Plugin):
    name = "Non GUI Plugin"
    description = "Non GUI Description"


def test_plugin_settings_schema_provider_empty() -> None:
    pm = PluginManager()
    pm.plugins = []
    provider = PluginSettingsSchemaProvider(pm)

    fields = provider.get_fields()
    assert fields == []


def test_plugin_settings_schema_provider_with_gui_plugins() -> None:
    pm = PluginManager()
    pm.plugins = [DummyGuiPlugin(), DummyNonGuiPlugin()]
    provider = PluginSettingsSchemaProvider(pm)

    fields = provider.get_fields()
    assert len(fields) == 1

    field = fields[0]
    assert field.key == "show_dummy_calendar_tab"
    assert field.label == "Show Dummy Calendar Tab"
    assert field.widget_type == WidgetType.CHECKBUTTON
    assert field.tab == "Modules"
    assert field.group == "Main Window Tabs"
    assert field.default is True
