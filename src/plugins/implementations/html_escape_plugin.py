from __future__ import annotations

import html
import logging

from src.plugins.base_plugin import TextPlugin

logger = logging.getLogger(__name__)

MAX_HTML_INPUT_LENGTH = 1_000_000  # 1MB: メモリ枯渇・DoS防止のための入力長制限 (#130)


class HTMLEscapePlugin(TextPlugin):
    """HTML特殊文字（&, <, >, ", '）をエスケープするプラグイン。"""

    @property
    def name(self) -> str:
        return "HTML Escape"

    @property
    def description(self) -> str:
        return "Escapes HTML special characters."

    def process(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return text

        if len(text) > MAX_HTML_INPUT_LENGTH:
            logger.warning(
                "HTMLエスケープ入力長が上限（%d文字）を超過しているためスキップします (現在: %d文字)",
                MAX_HTML_INPUT_LENGTH,
                len(text),
            )
            return text

        return html.escape(text)


class HTMLUnescapePlugin(TextPlugin):
    """HTML実体参照をデコード（アンエスケープ）するプラグイン。"""

    @property
    def name(self) -> str:
        return "HTML Unescape"

    @property
    def description(self) -> str:
        return "Unescapes HTML special characters."

    def process(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return text

        if len(text) > MAX_HTML_INPUT_LENGTH:
            logger.warning(
                "HTMLアンエスケープ入力長が上限（%d文字）を超過しているためスキップします (現在: %d文字)",
                MAX_HTML_INPUT_LENGTH,
                len(text),
            )
            return text

        return html.unescape(text)
