from .base_plugin import Plugin
import html

class HTMLEscapePlugin(Plugin):
    @property
    def name(self) -> str:
        return "HTML Escape/Unescape"

    @property
    def description(self) -> str:
        return "Escapes or unescapes HTML special characters."

    def process(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        # Heuristic: If text contains HTML entities, try to unescape
        # Otherwise, try to escape
        if '&amp;' in text or '&lt;' in text or '&gt;' in text or '&quot;' in text or '&#39;' in text:
            unescaped_text = html.unescape(text)
            if unescaped_text != text:
                return unescaped_text
        
        # If no entities found or unescaping didn't change, escape
        return html.escape(text)
