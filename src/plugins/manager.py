from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil

import src.plugins.implementations as plugins_package
from src.plugins.base_plugin import Plugin, TextPlugin
from src.plugins.gui_plugin import GuiPlugin

logger = logging.getLogger(__name__)


class PluginManager:
    def __init__(self) -> None:
        self.plugins: list[Plugin] = []
        self.load_plugins()

    def load_plugins(self) -> None:
        """実装パッケージ内で定義されたプラグインを動的に読み込む。"""
        self.plugins = []
        plugin_path = plugins_package.__path__
        plugin_prefix = plugins_package.__name__ + "."

        for _, name, _ in pkgutil.iter_modules(plugin_path, prefix=plugin_prefix):
            try:
                module = importlib.import_module(name)
                for class_name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        obj.__module__ == module.__name__
                        and issubclass(obj, Plugin)
                        and obj is not Plugin
                    ):
                        self.plugins.append(obj())
                        logger.info("Successfully loaded plugin: %s", class_name)
            except Exception as error:
                logger.error(
                    "Failed to load plugin from %s: %s", name, error, exc_info=True
                )

    def get_available_plugins(self) -> list[Plugin]:
        """読み込み済みの全プラグインを返す。"""
        return self.plugins

    def get_text_plugins(self) -> list[TextPlugin]:
        """テキスト変換を提供するプラグインを返す。"""
        return [plugin for plugin in self.plugins if isinstance(plugin, TextPlugin)]

    def get_gui_plugins(self) -> list[GuiPlugin]:
        """Tk GUIコンポーネントを提供するプラグインを返す。"""
        return [plugin for plugin in self.plugins if isinstance(plugin, GuiPlugin)]
