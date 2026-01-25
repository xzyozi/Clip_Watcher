from .base_plugin import Plugin


class LineSorterPlugin(Plugin):
    @property
    def name(self) -> str:
        return "Line Sorter"

    @property
    def description(self) -> str:
        return "Sorts lines of text alphabetically."

    def process(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        lines = text.splitlines()
        lines.sort()
        return '\n'.join(lines)
