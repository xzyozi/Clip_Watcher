"""src/core/platform/windows/clipboard_reader.py

Windows 用の win32clipboard を使用したクリップボード読み取り実装。

``pywin32`` はオプション依存のため、import は生成時に行う。未導入の環境では
``ImportError`` が送出されるので、呼び出し側（``PlatformServices``）が非対応として扱う。
"""

from __future__ import annotations

import logging
from typing import Any

from src.utils.clipboard_decode import decode_clipboard_data

logger = logging.getLogger(__name__)

_ERROR_ACCESS_DENIED = 5


class WindowsClipboardReader:
    """win32clipboard API を用いたクリップボードのテキスト読み取り。"""

    def __init__(self) -> None:
        # pywin32 未導入の場合は ImportError を送出する（呼び出し側で非対応扱い）
        import pywintypes
        import win32clipboard

        self._win32clipboard: Any = win32clipboard
        self._pywintypes: Any = pywintypes

    def read_text(self) -> str | None:
        """クリップボードのテキストを返す。

        失敗した場合は None、テキスト形式が処理できない場合は空文字を返す。
        """
        clip = self._win32clipboard
        try:
            clip.OpenClipboard()
            if clip.IsClipboardFormatAvailable(clip.CF_UNICODETEXT):
                return str(clip.GetClipboardData(clip.CF_UNICODETEXT))
            if clip.IsClipboardFormatAvailable(clip.CF_TEXT):
                return decode_clipboard_data(clip.GetClipboardData(clip.CF_TEXT))
            return ""  # 処理できないテキスト形式
        except self._pywintypes.error as e:
            if e.winerror == _ERROR_ACCESS_DENIED:
                logger.warning(
                    "win32clipboardがクリップボードを開けませんでした（アクセス拒否）。使用中の可能性があります。"
                )
            else:
                logger.error(
                    "win32clipboardフォールバックが予期せぬエラーで失敗しました: %s",
                    e,
                    exc_info=True,
                )
            return None
        except Exception as e:
            logger.error(
                "win32clipboardフォールバックが一般的なエラーで失敗しました: %s",
                e,
                exc_info=True,
            )
            return None
        finally:
            try:
                clip.CloseClipboard()
            except Exception:
                pass  # すでに閉じられている、または開けなかった
