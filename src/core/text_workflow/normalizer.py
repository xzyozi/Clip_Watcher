from __future__ import annotations

import unicodedata

# 個別ノーマライザー関数
def normalize_newlines(text: str) -> str:
    """CRLF や CR を LF に統一する"""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def trim_trailing_space(text: str) -> str:
    """各行の末尾の空白・タブをトリムする"""
    lines = text.split("\n")
    return "\n".join(line.rstrip(" \t") for line in lines)


def ensure_final_newline(text: str) -> str:
    """テキスト末尾に改行が無い場合、改行を1つ付与する"""
    if text and not text.endswith("\n"):
        return text + "\n"
    return text


def unicode_nfc(text: str) -> str:
    """Unicode 正規化 (NFC) を行う"""
    return unicodedata.normalize("NFC", text)


NORMALIZERS = {
    "normalize-newlines": normalize_newlines,
    "trim-trailing-space": trim_trailing_space,
    "ensure-final-newline": ensure_final_newline,
    "unicode-nfc": unicode_nfc,
}

DEFAULT_PROFILES = {
    "plain": ["normalize-newlines", "trim-trailing-space"],
    "strict": ["normalize-newlines", "trim-trailing-space", "ensure-final-newline", "unicode-nfc"],
}


class Normalizer:
    """テキストの正規化・整形を行うモジュール"""

    def __init__(self, custom_profiles: dict[str, list[str]] | None = None) -> None:
        self._profiles = {**DEFAULT_PROFILES, **(custom_profiles or {})}

    def normalize(self, text: str, profile_name: str = "plain") -> tuple[str, list[str]]:
        """
        指定プロファイルに従ってテキストを順次正規化し、(正規化後テキスト, 適用ノーマライザー名一覧) を返す。
        """
        applied: list[str] = []
        current = text
        normalizer_keys = self._profiles.get(profile_name, self._profiles.get("plain", []))

        for key in normalizer_keys:
            if key in NORMALIZERS:
                current = NORMALIZERS[key](current)
                applied.append(key)

        return current, applied
