from .base_plugin import Plugin


class DuplicateLineRemoverPlugin(Plugin):
    @property
    def name(self) -> str:
        return "Duplicate Line Remover"

    @property
    def description(self) -> str:
        return "Removes duplicate lines, preserving order."

    def process(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        seen_lines = set()
        unique_lines = []
        for line in text.splitlines():
            if line not in seen_lines:
                unique_lines.append(line)
                seen_lines.add(line)
        return '\n'.join(unique_lines)
