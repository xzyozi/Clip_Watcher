from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil

import src.plugins as plugins_package
from src.plugins.base_plugin import Plugin

logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self) -> None:
        self.plugins: list[Plugin] = []
        self.load_plugins()

    def load_plugins(self) -> None:
        """Dynamically load all plugins from the plugins package."""
        self.plugins = []
        plugin_path = plugins_package.__path__
        plugin_prefix = plugins_package.__name__ + "."

        for _, name, _ in pkgutil.iter_modules(plugin_path, prefix=plugin_prefix):
            try:
                module = importlib.import_module(name)
                for class_name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Plugin) and obj is not Plugin:
                        self.plugins.append(obj())
                        logger.info(f"Successfully loaded plugin: {class_name}")
            except Exception as e:
                logger.error(f"Failed to load plugin from {name}: {e}", exc_info=True)

    def get_available_plugins(self) -> list[Plugin]:
        """Return a list of all available plugin instances."""
        return self.plugins

    def get_text_plugins(self) -> list[Plugin]:
        """Return plugins that can process text."""
        text_plugins: list[Plugin] = []
        for plugin in self.plugins:
            # A plugin is a text plugin if its `process` method is different from the base class's.
            if plugin.process.__func__ is not Plugin.process.__func__: # type: ignore
                text_plugins.append(plugin)
        return text_plugins

    def get_gui_plugins(self) -> list[Plugin]:
        """Return plugins that have a GUI component."""
        return [p for p in self.plugins if p.has_gui_component()]
