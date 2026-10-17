from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass


@dataclass
class ClipboardHistoryDTO:
    """クリップボード履歴データのDTO"""

    content: str
    is_pinned: bool = False
    created_at: float = 0.0
    id: int | None = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()


MAX_CATEGORY_NAME_LENGTH = 100
MAX_METAPHRASE_TITLE_LENGTH = 200
MAX_METAPHRASE_CONTENT_LENGTH = 100_000


@dataclass
class CategoryDTO:
    """メタ管理カテゴリデータのDTO"""

    name: str
    sort_order: int = 0
    id: int | None = None

    def __post_init__(self) -> None:
        trimmed = self.name.strip()
        if not trimmed:
            raise ValueError("カテゴリ名を空にすることはできません。")
        if "\0" in self.name or "\r" in self.name or "\n" in self.name:
            raise ValueError(
                "カテゴリ名に不正な制御文字（NULLバイト、改行等）を含めることはできません。"
            )
        if len(trimmed) > MAX_CATEGORY_NAME_LENGTH:
            raise ValueError(
                f"カテゴリ名が長すぎます（最大 {MAX_CATEGORY_NAME_LENGTH} 文字、現在 {len(trimmed)} 文字）。"
            )
        self.name = trimmed


@dataclass
class MetaPhraseDTO:
    """カテゴリ別定型文（メタ文）データのDTO"""

    title: str
    content: str
    category_id: int
    sort_order: int = 0
    created_at: float = 0.0
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()

        if "\0" in self.title or "\r" in self.title or "\n" in self.title:
            raise ValueError(
                "定型文のタイトルに不正な制御文字（NULLバイト、改行等）を含めることはできません。"
            )
        trimmed_title = self.title.strip()
        if len(trimmed_title) > MAX_METAPHRASE_TITLE_LENGTH:
            raise ValueError(
                f"定型文のタイトルが長すぎます（最大 {MAX_METAPHRASE_TITLE_LENGTH} 文字、現在 {len(trimmed_title)} 文字）。"
            )
        self.title = trimmed_title

        trimmed_content = self.content.strip()
        if not trimmed_content:
            raise ValueError("定型文の本文を空にすることはできません。")
        if "\0" in self.content:
            raise ValueError(
                "定型文の本文に NULL バイト（\\0）を含めることはできません。"
            )
        if len(self.content) > MAX_METAPHRASE_CONTENT_LENGTH:
            raise ValueError(
                f"定型文の本文が長すぎます（最大 {MAX_METAPHRASE_CONTENT_LENGTH} 文字、現在 {len(self.content)} 文字）。"
            )
