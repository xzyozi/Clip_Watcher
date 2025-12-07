class ToolManager:
    def __init__(self):
        self._tools = {}

    def register_tool(self, name, command):
        """Registers a tool with a given name and its associated command (callable)."""
        if name in self._tools:
            raise ValueError(f"Tool with name '{name}' already registered.")
        self._tools[name] = command

    def get_tool_command(self, name):
        """Retrieves the command associated with a tool name."""
        return self._tools.get(name)

    def get_all_tool_names(self):
        """Returns a list of all registered tool names."""
        return list(self._tools.keys())
