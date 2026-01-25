import re

from .base_plugin import Plugin


def to_snake_case(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower().replace('-', '_')

def to_camel_case(name: str) -> str:
    s = to_snake_case(name).split('_')
    return s[0] + ''.join(word.capitalize() for word in s[1:])

def to_pascal_case(name: str) -> str:
    return ''.join(word.capitalize() for word in to_snake_case(name).split('_'))

def to_kebab_case(name: str) -> str:
    return to_snake_case(name).replace('_', '-')

class GeneralCaseConverterPlugin(Plugin):
    @property
    def name(self) -> str:
        return "Case Converter"

    @property
    def description(self) -> str:
        return "Converts text between snake_case, camelCase, PascalCase, and kebab-case."

    def process(self, text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            return text

        # Simple heuristic to detect current case and cycle through
        # This is a very basic implementation and can be improved.
        if '_' in text: # Likely snake_case
            return to_camel_case(text)
        elif '-' in text: # Likely kebab-case
            return to_pascal_case(text)
        elif re.match(r'^[a-z]+([A-Z][a-z0-9]*)*$', text): # Likely camelCase
            return to_snake_case(text)
        elif re.match(r'^([A-Z][a-z0-9]*)+$', text): # Likely PascalCase
            return to_kebab_case(text)
        else: # Default to snake_case if no clear pattern
            return to_snake_case(text)
