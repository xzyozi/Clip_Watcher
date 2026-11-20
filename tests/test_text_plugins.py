"""テキスト変換プラグイン（Base64 / CSV / ケース変換 / テーブル整形）の単体テスト。"""

from __future__ import annotations

import base64

import pytest

from src.plugins.implementations.base64_converter_plugin import Base64ConverterPlugin
from src.plugins.implementations.csv_formatter_plugin import CSVFormatterPlugin
from src.plugins.implementations.general_case_converter_plugin import (
    GeneralCaseConverterPlugin,
    to_camel_case,
    to_kebab_case,
    to_pascal_case,
    to_snake_case,
)
from src.plugins.implementations.table_formatter_plugin import TableFormatterPlugin

# --- Base64 ---


def test_base64_plugin_metadata() -> None:
    plugin = Base64ConverterPlugin()
    assert plugin.name == "Base64 Encode/Decode"
    assert plugin.description


def test_base64_encodes_plain_text() -> None:
    assert Base64ConverterPlugin().process("hello!") == "aGVsbG8h"


def test_base64_decodes_printable_base64() -> None:
    encoded = base64.b64encode(b"hello world").decode("ascii")
    assert Base64ConverterPlugin().process(encoded) == "hello world"


def test_base64_encodes_when_decoded_bytes_are_not_printable() -> None:
    # 長さ4の倍数・有効な Base64 だが、復号結果が制御文字になるためエンコード側へ倒れる
    text = base64.b64encode(b"\x01\x02\x03\x04").decode("ascii")
    assert Base64ConverterPlugin().process(text) == base64.b64encode(
        text.encode("utf-8")
    ).decode("ascii")


def test_base64_encodes_when_decoded_bytes_are_not_utf8() -> None:
    text = base64.b64encode(b"\xff\xfe\xfd\xfc").decode("ascii")
    assert Base64ConverterPlugin().process(text) == base64.b64encode(
        text.encode("utf-8")
    ).decode("ascii")


def test_base64_returns_non_string_unchanged() -> None:
    assert Base64ConverterPlugin().process(123) == 123  # type: ignore[arg-type]


# --- CSV/TSV ---


def test_csv_formatter_metadata() -> None:
    plugin = CSVFormatterPlugin()
    assert plugin.name == "CSV/TSV Formatter"
    assert plugin.description


@pytest.mark.parametrize("text", ["", "   \n", None])
def test_csv_formatter_returns_blank_or_non_string_unchanged(text: object) -> None:
    assert CSVFormatterPlugin().process(text) == text  # type: ignore[arg-type]


def test_csv_formatter_aligns_comma_separated_columns() -> None:
    result = CSVFormatterPlugin().process("a,bbb\ncccc,d")
    assert result.split("\n") == ["a   ,bbb", "cccc,d  "]


def test_csv_formatter_uses_tab_when_only_tabs_present() -> None:
    result = CSVFormatterPlugin().process("a\tbb\nccc\td")
    assert result.split("\n") == ["a  \tbb", "ccc\td "]


def test_csv_formatter_prefers_tab_when_tabs_outnumber_commas() -> None:
    result = CSVFormatterPlugin().process("a\tb\tc,x\nd\te\tf")
    # タブ数 (4) がカンマ数 (1) より多いのでタブ区切りとして扱う
    assert "\t" in result
    assert result.split("\n")[0].split("\t")[2] == "c,x"


def test_csv_formatter_prefers_comma_when_commas_outnumber_tabs() -> None:
    result = CSVFormatterPlugin().process("a,b,c\td\ne,f,g")
    assert result.split("\n")[0].startswith("a,b,")


def test_csv_formatter_returns_original_when_csv_is_invalid() -> None:
    # 閉じていない引用符は csv.reader（strict）でエラーになる前提の入力ではないため、
    # フィールド上限超過で csv.Error を発生させる
    import csv

    original_limit = csv.field_size_limit()
    csv.field_size_limit(10)
    try:
        text = "x" * 50 + ",y"
        assert CSVFormatterPlugin().process(text) == text
    finally:
        csv.field_size_limit(original_limit)


# --- ケース変換 ---


@pytest.mark.parametrize(
    ("func", "source", "expected"),
    [
        (to_snake_case, "helloWorld", "hello_world"),
        (to_snake_case, "HelloWorld", "hello_world"),
        (to_snake_case, "hello-world", "hello_world"),
        (to_camel_case, "hello_world_text", "helloWorldText"),
        (to_pascal_case, "hello_world", "HelloWorld"),
        (to_kebab_case, "helloWorld", "hello-world"),
    ],
)
def test_case_helper_functions(func: object, source: str, expected: str) -> None:
    assert func(source) == expected  # type: ignore[operator]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hello_world", "helloWorld"),  # snake -> camel
        ("hello-world", "HelloWorld"),  # kebab -> Pascal
        ("helloWorld", "hello_world"),  # camel -> snake
        ("HelloWorld", "hello-world"),  # Pascal -> kebab
        ("HELLO world", "hello world"),  # 判定不能 -> snake 変換（小文字化）
    ],
)
def test_general_case_converter_cycles_through_styles(text: str, expected: str) -> None:
    assert GeneralCaseConverterPlugin().process(text) == expected


@pytest.mark.parametrize("text", ["", "  ", None])
def test_general_case_converter_returns_blank_or_non_string_unchanged(
    text: object,
) -> None:
    assert GeneralCaseConverterPlugin().process(text) == text  # type: ignore[arg-type]


def test_general_case_converter_metadata() -> None:
    plugin = GeneralCaseConverterPlugin()
    assert plugin.name == "Case Converter"
    assert "snake_case" in plugin.description


# --- テーブル整形 ---


def test_table_formatter_metadata() -> None:
    plugin = TableFormatterPlugin()
    assert plugin.name == "Table Formatter"
    assert plugin.description


def test_table_formatter_returns_blank_text_unchanged() -> None:
    assert TableFormatterPlugin().process("  \n") == "  \n"


def test_table_formatter_returns_text_without_delimiter_unchanged() -> None:
    assert TableFormatterPlugin().process("plain text") == "plain text"


def test_table_formatter_formats_comma_separated_text() -> None:
    result = TableFormatterPlugin().process("name, age\nalice,30")
    assert result.split("\n") == ["name  | age", "alice | 30 "]


def test_table_formatter_formats_tab_separated_text() -> None:
    result = TableFormatterPlugin().process("a\tbb\nccc\td")
    assert result.split("\n") == ["a   | bb", "ccc | d "]


def test_table_formatter_pads_short_rows() -> None:
    result = TableFormatterPlugin().process("a,b,c\nd")
    assert result.split("\n") == ["a | b | c", "d |   |  "]


def test_table_formatter_returns_original_when_formatting_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.plugins.implementations.table_formatter_plugin as module

    def broken_reader(*args: object, **kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(module.csv, "reader", broken_reader)
    assert TableFormatterPlugin().process("a,b") == "a,b"
