"""クリップボードから取得したデータを文字列へ正規化するユーティリティ。"""

from __future__ import annotations

from typing import Any

_FALLBACK_ENCODINGS = ("utf-8", "shift-jis", "cp932", "euc-jp", "latin1")


def decode_clipboard_data(data: Any) -> str:
    """bytes / str / その他のクリップボードデータを文字列へ変換する。"""
    if isinstance(data, bytes):
        for encoding in _FALLBACK_ENCODINGS:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore")
    if isinstance(data, str):
        try:
            return data.encode("utf-8", errors="surrogateescape").decode(
                "utf-8", errors="ignore"
            )
        except Exception:
            return data
    return str(data)
