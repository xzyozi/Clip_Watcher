import inspect
import logging
import src.plugins as plugins_package
from src.plugins import Plugin

logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self):
        self.plugins = []
        self.load_plugins()

    def load_plugins(self):
        """Dynamically load all plugins from the plugins package."""
        try:
            for name, obj in inspect.getmembers(plugins_package, inspect.isclass):
                if issubclass(obj, Plugin) and obj is not Plugin:
                    self.plugins.append(obj())
        except Exception as e:
            logger.error(f"Failed to load plugins: {e}", exc_info=True)

    def get_available_plugins(self):
        """Return a list of all available plugin instances."""
        return self.plugins