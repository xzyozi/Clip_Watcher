"""tests/test_i18n.py

Translator の JSON 型検証・不正エントリスキップ・絶対パス解決テスト（#138, #176）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.utils.i18n import Translator


def _mock_settings_manager(language: object = "en") -> MagicMock:
    sm = MagicMock()
    sm.get_setting.return_value = language
    sm.event_dispatcher = MagicMock()
    return sm


def test_default_locales_dir_resolves_independently_of_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """カレントディレクトリが別ディレクトリでも __file__ 基準で locales を読み込める。"""
    monkeypatch.chdir(tmp_path)
    sm = _mock_settings_manager("en")

    translator = Translator(sm)

    assert Path(translator.locales_dir).is_absolute()
    assert "en" in translator.translations
    assert "ja" in translator.translations


def test_non_dict_json_root_is_skipped_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """ルートが list / str / int などの非辞書 JSON でもクラッシュせず警告してスキップする。"""
    (tmp_path / "en.json").write_text(json.dumps({"hello": "Hello"}), encoding="utf-8")
    (tmp_path / "ja.json").write_text(
        json.dumps(["not", "a", "dict"]), encoding="utf-8"
    )

    sm = _mock_settings_manager("ja")
    with caplog.at_level(logging.WARNING, logger="src.utils.i18n"):
        translator = Translator(sm, locales_dir=tmp_path)

    assert "ja" not in translator.translations
    assert translator.translate("hello") == "Hello"
    assert translator.translate("missing_key") == "missing_key"
    assert any("expected dict" in r.getMessage() for r in caplog.records)


def test_valid_string_and_string_list_entries_are_loaded(tmp_path: Path) -> None:
    """文字列（str）および文字列リスト（list[str]）は正常に読み込まれる。"""
    (tmp_path / "en.json").write_text(
        json.dumps(
            {
                "valid_key": "Valid Text",
                "days_short": ["Sun", "Mon", "Tue"],
            }
        ),
        encoding="utf-8",
    )

    sm = _mock_settings_manager("en")
    translator = Translator(sm, locales_dir=tmp_path)

    assert translator.translate("valid_key") == "Valid Text"
    assert translator.translate("days_short") == ["Sun", "Mon", "Tue"]
    assert translator("days_short") == ["Sun", "Mon", "Tue"]


def test_invalid_entries_in_json_dict_are_filtered_out(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """数値・null・入れ子dict・非文字列要素を含むリスト等はスキップし、正常な項目は保持する。"""
    (tmp_path / "en.json").write_text(
        json.dumps(
            {
                "valid_key": "Valid Text",
                "valid_list": ["a", "b"],
                "num_val": 123,
                "null_val": None,
                "dict_val": {"nested": "value"},
                "mixed_list": ["a", 1],
                "int_list": [1, 2],
            }
        ),
        encoding="utf-8",
    )

    sm = _mock_settings_manager("en")
    with caplog.at_level(logging.WARNING, logger="src.utils.i18n"):
        translator = Translator(sm, locales_dir=tmp_path)

    assert translator.translate("valid_key") == "Valid Text"
    assert translator.translate("valid_list") == ["a", "b"]
    assert translator.translate("num_val") == "num_val"
    assert translator.translate("null_val") == "null_val"
    assert translator.translate("dict_val") == "dict_val"
    assert translator.translate("mixed_list") == "mixed_list"
    assert translator.translate("int_list") == "int_list"
    assert (
        sum("non-string translation entry" in r.getMessage() for r in caplog.records)
        == 5
    )


def test_real_locales_load_calendar_weekday_lists() -> None:
    """実際の locales/ ディレクトリから days_short と weekdays_full が正しく読み込める。"""
    sm = _mock_settings_manager("ja")
    translator = Translator(sm)

    ja_days = translator("days_short")
    assert isinstance(ja_days, list)
    assert ja_days == ["日", "月", "火", "水", "木", "金", "土"]

    ja_weekdays = translator("weekdays_full")
    assert isinstance(ja_weekdays, list)
    assert ja_weekdays == ["月", "火", "水", "木", "金", "土", "日"]
