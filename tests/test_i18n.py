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


def test_non_string_values_in_json_dict_are_filtered_out(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """辞書内の非文字列値（数値・リスト・null 等）はスキップし、正常な文字列項目は保持する。"""
    (tmp_path / "en.json").write_text(
        json.dumps(
            {
                "valid_key": "Valid Text",
                "num_val": 123,
                "list_val": ["a"],
                "null_val": None,
            }
        ),
        encoding="utf-8",
    )

    sm = _mock_settings_manager("en")
    with caplog.at_level(logging.WARNING, logger="src.utils.i18n"):
        translator = Translator(sm, locales_dir=tmp_path)

    assert translator.translate("valid_key") == "Valid Text"
    assert translator.translate("num_val") == "num_val"
    assert (
        sum("non-string translation entry" in r.getMessage() for r in caplog.records)
        == 3
    )
