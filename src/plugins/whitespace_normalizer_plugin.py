from .base_plugin import Plugin


class WhitespaceNormalizerPlugin(Plugin):
    @property
    def name(self) -> str:
        return "Whitespace Normalizer"

    @property
    def description(self) -> str:
        return "Removes extra whitespace, normalizes spaces and line endings."

    def process(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        lines = text.splitlines()
        normalized_lines = []
        for line in lines:
            # Remove leading/trailing whitespace from the line
            line = line.strip()
            # Replace multiple spaces with a single space
            line = ' '.join(line.split())
            # Replace tabs with spaces
            line = line.replace('	', ' ')
            normalized_lines.append(line)

        # Join lines with normalized line endings
        return '\n'.join(normalized_lines)
