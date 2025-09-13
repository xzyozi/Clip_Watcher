import json
from .base_plugin import Plugin

class JSONFormatterPlugin(Plugin):
    @property
    def name(self) -> str:
        return "JSON Formatter"

    @property
    def description(self) -> str:
        return "Formats a string if it is a valid JSON."

    def process(self, text: str) -> str:
        try:
            # Attempt to load the text as JSON
            json_object = json.loads(text)
            # If successful, dump it back to a string with indentation
            return json.dumps(json_object, indent=4, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            # If it's not a valid JSON string or not a string at all, return original text
            return text
