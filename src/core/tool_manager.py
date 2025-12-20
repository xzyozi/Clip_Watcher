import inspect
import logging
import src.gui.components as tool_components_package
from src.gui.components.base_tool_component import BaseToolComponent

logger = logging.getLogger(__name__)

import inspect
import logging
import src.gui.components as tool_components_package
from src.gui.components.base_tool_component import BaseToolComponent

logger = logging.getLogger(__name__)

class ToolManager:
    def __init__(self):
        self.tools = {}
        self.load_tools()

    def load_tools(self):
        """Dynamically load all tool components from the gui.components package."""
        try:
            for name, obj in inspect.getmembers(tool_components_package, inspect.isclass):
                if issubclass(obj, BaseToolComponent) and obj is not BaseToolComponent:
                    # We need an instance to get the tool_name property.
                    # This assumes the tool component can be instantiated with no arguments
                    # for the purpose of getting its name. This is a limitation.
                    # A better way might be a class-level variable.
                    # For now, we can't get the name without an instance.
                    # Let's defer getting the name until the GUI needs it.
                    # We will store the classes and let the GUI part instantiate them.
                    self.tools[obj.__name__] = obj
            logger.info(f"Loaded {len(self.tools)} tool components.")
        except Exception as e:
            logger.error(f"Failed to load tool components: {e}", exc_info=True)

    def get_tool_class(self, name: str):
        """Retrieves the class for a given tool name."""
        # This method might need to map from a friendly name to a class name if they differ
        for tool_class in self.tools.values():
            # This still requires instantiation to get the name.
            # This design needs to be re-thought.
            # Let's change the plan. The GUI will get the classes and instantiate them.
            if tool_class.__name__ == name:
                return tool_class
        return None

    def get_all_tool_classes(self):
        """Return a list of all available tool classes."""
        return list(self.tools.values())


