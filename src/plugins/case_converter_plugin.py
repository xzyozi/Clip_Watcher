from .base_plugin import Plugin

class CaseConverterPlugin(Plugin):
    @property
    def name(self) -> str:
        return "Uppercase Converter"

    @property
    def description(self) -> str:
        return "Converts the text to uppercase."

    def process(self, text: str) -> str:
        if isinstance(text, str):
            return text.upper()
        return text
