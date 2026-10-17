from __future__ import annotations

import json
import logging

from src.plugins.base_plugin import TextPlugin

logger = logging.getLogger(__name__)

MAX_JSON_INPUT_LENGTH = 1_000_000  # 1MB: メモリ枯渇・DoS防止のための入力長制限 (#128)


class JSONFormatterPlugin(TextPlugin):
    @property
    def name(self) -> str:
        return "JSON Formatter"

    @property
    def description(self) -> str:
        return "Formats a string if it is a valid JSON."

    def process(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return text

        if len(text) > MAX_JSON_INPUT_LENGTH:
            logger.warning(
                "JSON入力長が上限（%d文字）を超過しているため整形をスキップします (現在: %d文字)",
                MAX_JSON_INPUT_LENGTH,
                len(text),
            )
            return text

        try:
            # Attempt to load the text as JSON
            json_object = json.loads(text)
            # If successful, dump it back to a string with indentation
            return json.dumps(json_object, indent=4, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError, ValueError, RecursionError):
            return text
        except Exception as e:
            logger.warning("JSON整形処理中に予期せぬエラーが発生しました: %s", e)
            return text
