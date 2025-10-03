import os
import importlib
import inspect
from src.plugins.base_plugin import Plugin
import logging

logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self):
        self.plugins = []
        self.load_plugins()

    def load_plugins(self):
        """Dynamically load all plugins from the plugins directory."""
        plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        plugin_files = [f for f in os.listdir(plugins_dir) if f.endswith('_plugin.py')]

        for plugin_file in plugin_files:
            module_name = f"src.plugins.{plugin_file[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Plugin) and obj is not Plugin:
                        self.plugins.append(obj())
            except Exception as e:
                logger.info(f"Failed to load plugin {module_name}: {e}")

    def get_available_plugins(self):
        """Return a list of all available plugin instances."""
        return self.plugins