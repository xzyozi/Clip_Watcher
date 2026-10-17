from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from src.db.dao.category_dao import CategoryDAO
from src.db.dao.meta_phrase_dao import MetaPhraseDAO
from src.db.dto import (
    MAX_CATEGORY_NAME_LENGTH,
    MAX_METAPHRASE_CONTENT_LENGTH,
    MAX_METAPHRASE_TITLE_LENGTH,
    CategoryDTO,
    MetaPhraseDTO,
)


def test_category_dto_trimming_and_valid() -> None:
    """CategoryDTO が正常値を受け入れ、前後の空白を自動トリムすることを検証 (#122)。"""
    dto = CategoryDTO(name="  開発用定型文  ")
    assert dto.name == "開発用定型文"


def test_category_dto_empty_reject() -> None:
    """CategoryDTO が空文字および空白のみを拒否することを検証 (#122)。"""
    with pytest.raises(ValueError, match="カテゴリ名を空にすることはできません"):
        CategoryDTO(name="")

    with pytest.raises(ValueError, match="カテゴリ名を空にすることはできません"):
        CategoryDTO(name="   \t  ")


def test_category_dto_control_characters_reject() -> None:
    """CategoryDTO が NULL バイトや改行などの制御文字を拒否することを検証 (#122)。"""
    with pytest.raises(ValueError, match="不正な制御文字"):
        CategoryDTO(name="Bad\0Name")

    with pytest.raises(ValueError, match="不正な制御文字"):
        CategoryDTO(name="Bad\nName")

    with pytest.raises(ValueError, match="不正な制御文字"):
        CategoryDTO(name="Bad\rName")


def test_category_dto_max_length_validation() -> None:
    """CategoryDTO が最大長（100文字）を超過した場合に拒否し、境界値を許容することを検証 (#122)。"""
    exact = "A" * MAX_CATEGORY_NAME_LENGTH
    dto = CategoryDTO(name=exact)
    assert len(dto.name) == MAX_CATEGORY_NAME_LENGTH

    too_long = "A" * (MAX_CATEGORY_NAME_LENGTH + 1)
    with pytest.raises(ValueError, match="カテゴリ名が長すぎます"):
        CategoryDTO(name=too_long)


def test_metaphrase_dto_title_validation() -> None:
    """MetaPhraseDTO のタイトルのトリム、空文字、制御文字、最大長検証 (#122)。"""
    dto = MetaPhraseDTO(title="  タイトル  ", content="本文", category_id=1)
    assert dto.title == "タイトル"

    # 空タイトルおよび空白のみは空文字として許容されること
    dto_empty = MetaPhraseDTO(title="   ", content="本文", category_id=1)
    assert dto_empty.title == ""

    with pytest.raises(ValueError, match="不正な制御文字"):
        MetaPhraseDTO(title="Title\0WithNull", content="本文", category_id=1)

    with pytest.raises(ValueError, match="不正な制御文字"):
        MetaPhraseDTO(title="Title\nWithNewline", content="本文", category_id=1)

    exact_title = "T" * MAX_METAPHRASE_TITLE_LENGTH
    dto_exact = MetaPhraseDTO(title=exact_title, content="本文", category_id=1)
    assert len(dto_exact.title) == MAX_METAPHRASE_TITLE_LENGTH

    too_long_title = "T" * (MAX_METAPHRASE_TITLE_LENGTH + 1)
    with pytest.raises(ValueError, match="定型文のタイトルが長すぎます"):
        MetaPhraseDTO(title=too_long_title, content="本文", category_id=1)


def test_metaphrase_dto_content_validation() -> None:
    """MetaPhraseDTO の本文の空文字、NULLバイト、最大長検証、および複数行許可の検証 (#122)。"""
    # 複数行の本文は正常に許可されること
    multiline = "Line 1\nLine 2\r\nLine 3"
    dto = MetaPhraseDTO(title="タイトル", content=multiline, category_id=1)
    assert dto.content == multiline

    # 空文字の拒否
    with pytest.raises(ValueError, match="定型文の本文を空にすることはできません"):
        MetaPhraseDTO(title="タイトル", content="   \t\n  ", category_id=1)

    # NULLバイトの拒否
    with pytest.raises(ValueError, match="NULL バイト"):
        MetaPhraseDTO(title="タイトル", content="Hello\0World", category_id=1)

    # 最大長超過の拒否
    too_long_content = "C" * (MAX_METAPHRASE_CONTENT_LENGTH + 1)
    with pytest.raises(ValueError, match="定型文の本文が長すぎます"):
        MetaPhraseDTO(title="タイトル", content=too_long_content, category_id=1)


def test_dao_validates_mutated_dto(tmp_path: Path) -> None:
    """生成後に属性が不正に変更されたDTOが DAO.add / update 時に拒否されることを検証 (#122)。"""
    db_file = tmp_path / "dao_validation.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "CREATE TABLE t_category (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, sort_order INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute(
        "CREATE TABLE t_meta_phrase (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, content TEXT NOT NULL, category_id INTEGER NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL)"
    )
    conn.commit()
    conn.close()

    lock = threading.Lock()
    cat_dao = CategoryDAO(str(db_file), lock)
    meta_dao = MetaPhraseDAO(str(db_file), lock)

    dto = CategoryDTO(name="Valid")
    dto.name = ""  # 直接属性を不正値に改ざん
    with pytest.raises(ValueError):
        cat_dao.add(dto)

    dto.id = 1
    with pytest.raises(ValueError):
        cat_dao.update(dto)

    m_dto = MetaPhraseDTO(title="Valid Title", content="Valid Content", category_id=1)
    m_dto.content = "   "  # 直接本文を不正値に改ざん
    with pytest.raises(ValueError):
        meta_dao.add(m_dto)

    m_dto.id = 1
    with pytest.raises(ValueError):
        meta_dao.update(m_dto)
