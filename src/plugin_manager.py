import os
import importlib
import inspect
from src.plugins.base_plugin import Plugin
from src.settings_manager import SettingsManager

class PluginManager:
    def __init__(self, settings_manager: SettingsManager):
        self.settings_manager = settings_manager
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
                print(f"Failed to load plugin {module_name}: {e}")

    def apply_plugins(self, text: str) -> str:
        """Apply all enabled plugins to the text."""
        processed_text = text
        plugin_settings = self.settings_manager.get_setting("plugins", {})
        
        for plugin in self.plugins:
            # Use plugin's class name as the key in settings
            plugin_key = plugin.__class__.__name__
            if plugin_settings.get(plugin_key, False): # Default to disabled
                try:
                    processed_text = plugin.process(processed_text)
                except Exception as e:
                    print(f"Error processing with plugin {plugin.name}: {e}")
        return processed_text

    def get_available_plugins(self):
        """Return a list of all available plugin instances."""
        return self.plugins
