from .base_plugin import Plugin
import urllib.parse

class URLConverterPlugin(Plugin):
    @property
    def name(self) -> str:
        return "URL Encode/Decode"

    @property
    def description(self) -> str:
        return "Encodes or decodes URL strings."

    def process(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        # Heuristic to check if text is URL-encoded
        # If it contains '%' followed by two hex digits, it's likely URL-encoded
        # This is a simple check and might not be foolproof for all cases.
        if '%' in text and any(c.isalnum() for c in text.split('%', 1)[1][:2]):
            try:
                # Attempt to decode
                decoded_text = urllib.parse.unquote(text)
                # Only return if decoding actually changed something
                if decoded_text != text:
                    return decoded_text
            except Exception:
                pass # Fallback to encoding if decoding fails or doesn't change

        # If not URL-encoded or decoding failed/didn't change, attempt to encode
        return urllib.parse.quote(text, safe='') # Encode all characters
