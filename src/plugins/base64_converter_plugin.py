import base64

from .base_plugin import Plugin


class Base64ConverterPlugin(Plugin):
    @property
    def name(self) -> str:
        return "Base64 Encode/Decode"

    @property
    def description(self) -> str:
        return "Encodes or decodes Base64 strings."

    def process(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        # Heuristic to check if text is Base64 encoded
        # Base64 strings typically contain A-Z, a-z, 0-9, +, /, =
        # and their length is a multiple of 4 (padding with '=')
        if len(text) % 4 == 0:
            try:
                # Attempt to decode
                decoded_bytes = base64.b64decode(text, validate=True)
                decoded_text = decoded_bytes.decode('utf-8') # Assume UTF-8 for decoded text

                # Check if decoded text is printable and doesn't contain too many control characters
                # This is a heuristic to avoid decoding random binary data into garbage text
                if all(32 <= ord(c) <= 126 or c in '\n\r\t' for c in decoded_text):
                    return decoded_text
            except Exception:
                pass # Not a valid base64 string or not decodable/printable
        # If not Base64 encoded or decoding failed/resulted in non-printable, attempt to encode
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')
