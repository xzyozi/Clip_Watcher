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
            self.content_hash = hashlib.sha256(self.content.encode('utf-8')).hexdigest()

@dataclass
class CategoryDTO:
    """メタ管理カテゴリデータのDTO"""
    name: str
    sort_order: int = 0
    id: int | None = None

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
