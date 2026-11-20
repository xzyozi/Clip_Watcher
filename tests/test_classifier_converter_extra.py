"""Classifier の条件評価と UnitConverterComponent の変換ロジックの補足テスト。

正規表現の安全評価は、子プロセス（spawn）を起動せず偽のコンテキストで検証する。
"""

from __future__ import annotations

import re
import tkinter as tk
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.text_workflow import classifier as classifier_module
from src.core.text_workflow.classifier import (
    DEFAULT_REGEX_MAX_PATTERN_LENGTH,
    DEFAULT_REGEX_TIMEOUT_SECONDS,
    Classifier,
    _search_regex_in_subprocess,
)
from src.plugins.implementations.unit_converter_plugin import (
    MAX_CONVERTER_INPUT_LENGTH,
    UnitConverterComponent,
)

# --- Classifier: 設定値の検証 ---


@pytest.mark.parametrize("bad_length", [0, -5, True, "200", 1.5])
def test_invalid_regex_length_falls_back_to_default(bad_length: Any) -> None:
    instance = Classifier(regex_max_pattern_length=bad_length)
    assert instance._regex_max_pattern_length == DEFAULT_REGEX_MAX_PATTERN_LENGTH


@pytest.mark.parametrize("bad_timeout", [0, -1, True, "1"])
def test_invalid_regex_timeout_falls_back_to_default(bad_timeout: Any) -> None:
    instance = Classifier(regex_timeout_seconds=bad_timeout)
    assert instance._regex_timeout_seconds == DEFAULT_REGEX_TIMEOUT_SECONDS


def test_valid_regex_settings_are_kept() -> None:
    instance = Classifier(regex_max_pattern_length=50, regex_timeout_seconds=2)
    assert (instance._regex_max_pattern_length, instance._regex_timeout_seconds) == (
        50,
        2.0,
    )


# --- Classifier: 分類ルール ---


def test_category_hint_wins_over_rules() -> None:
    rules = [
        {"id": "r", "categoryId": "code", "when": {"kind": "contains", "value": "x"}}
    ]
    result = Classifier(rules).classify("x", category_hint="memo")
    assert (result.category_id, result.tags) == ("memo", ["hinted"])


def test_rules_are_ordered_by_priority_and_skip_disabled() -> None:
    rules = [
        {
            "id": "b",
            "priority": 20,
            "categoryId": "second",
            "when": {"kind": "contains", "value": "a"},
        },
        {
            "id": "a",
            "priority": 10,
            "categoryId": "first",
            "tags": ["t"],
            "when": {"kind": "contains", "value": "a"},
        },
        {
            "id": "off",
            "priority": 1,
            "enabled": False,
            "categoryId": "disabled",
            "when": {"kind": "contains", "value": "a"},
        },
    ]
    result = Classifier(rules).classify("abc")
    assert (result.category_id, result.matched_rule_id, result.tags) == (
        "first",
        "a",
        ["t"],
    )


def test_unmatched_text_uses_default_category() -> None:
    result = Classifier(
        [{"id": "r", "when": {"kind": "contains", "value": "zzz"}}],
        default_category="other",
    ).classify("abc")
    assert (result.category_id, result.confidence) == ("other", 0.0)


def test_matching_rule_without_category_uses_default_category() -> None:
    result = Classifier(
        [{"id": "r", "when": {"kind": "contains", "value": "a"}}],
        default_category="fallback",
    ).classify("abc")
    assert result.category_id == "fallback"
    assert result.matched_rule_id == "r"


@pytest.mark.parametrize(
    ("condition", "text", "expected"),
    [
        ({}, "abc", False),
        ({"kind": "contains", "value": "b"}, "abc", True),
        ({"kind": "contains", "value": ""}, "abc", False),
        ({"kind": "containsAny", "values": ["x", "c"]}, "abc", True),
        ({"kind": "containsAny", "values": []}, "abc", False),
        ({"kind": "minLength", "value": 3}, "abc", True),
        ({"kind": "minLength", "value": 4}, "abc", False),
        ({"kind": "maxLength", "value": 3}, "abc", True),
        ({"kind": "maxLength", "value": 2}, "abc", False),
        ({"kind": "maxLength"}, "abc", True),
        ({"kind": "unknown"}, "abc", False),
        ({"kind": "regex"}, "abc", False),
        (
            {
                "all": [
                    {"kind": "contains", "value": "a"},
                    {"kind": "contains", "value": "c"},
                ]
            },
            "abc",
            True,
        ),
        (
            {
                "all": [
                    {"kind": "contains", "value": "a"},
                    {"kind": "contains", "value": "z"},
                ]
            },
            "abc",
            False,
        ),
        (
            {
                "any": [
                    {"kind": "contains", "value": "z"},
                    {"kind": "contains", "value": "c"},
                ]
            },
            "abc",
            True,
        ),
        ({"not": {"kind": "contains", "value": "z"}}, "abc", True),
    ],
)
def test_condition_evaluation(
    condition: dict[str, Any], text: str, expected: bool
) -> None:
    assert Classifier()._evaluate_condition(condition, text) is expected


# --- Classifier: 正規表現の安全評価（偽の子プロセス） ---


def _fake_context(
    *, alive_after_join: bool, poll: bool = True, recv: Any = True
) -> tuple[MagicMock, MagicMock, MagicMock]:
    receiver = MagicMock()
    receiver.poll.return_value = poll
    if isinstance(recv, BaseException):
        receiver.recv.side_effect = recv
    else:
        receiver.recv.return_value = recv
    sender = MagicMock()
    process = MagicMock()
    process.is_alive.side_effect = [alive_after_join, False]
    context = MagicMock()
    context.Pipe.return_value = (receiver, sender)
    context.Process.return_value = process
    return context, receiver, process


def _evaluate(context: MagicMock, pattern: str = "a+") -> bool:
    with patch.object(
        classifier_module.multiprocessing, "get_context", return_value=context
    ):
        return Classifier()._evaluate_regex_safely(pattern, "aaa")


def test_regex_result_is_read_from_child_process() -> None:
    context, receiver, process = _fake_context(alive_after_join=False, recv=True)
    assert _evaluate(context) is True
    process.start.assert_called_once()
    process.close.assert_called_once()
    receiver.close.assert_called_once()


def test_regex_without_result_is_treated_as_no_match() -> None:
    context, _, _ = _fake_context(alive_after_join=False, poll=False)
    assert _evaluate(context) is False


def test_regex_child_crash_is_treated_as_no_match() -> None:
    context, _, _ = _fake_context(alive_after_join=False, recv=EOFError())
    assert _evaluate(context) is False


def test_regex_timeout_terminates_child_process() -> None:
    context, _, process = _fake_context(alive_after_join=True)
    assert _evaluate(context) is False
    process.terminate.assert_called_once()


def test_regex_pattern_too_long_is_rejected_without_process() -> None:
    context, _, process = _fake_context(alive_after_join=False)
    assert _evaluate(context, "a" * (DEFAULT_REGEX_MAX_PATTERN_LENGTH + 1)) is False
    process.start.assert_not_called()


def test_invalid_regex_is_rejected_without_process() -> None:
    context, _, process = _fake_context(alive_after_join=False)
    assert _evaluate(context, "(unclosed") is False
    process.start.assert_not_called()


def test_regex_condition_delegates_to_safe_evaluator() -> None:
    instance = Classifier()
    with patch.object(instance, "_evaluate_regex_safely", return_value=True) as safe:
        assert instance._evaluate_condition({"kind": "regex", "pattern": "a"}, "a")
    safe.assert_called_once_with("a", "a")


@pytest.mark.parametrize(
    ("pattern", "text", "expected"),
    [("a+", "caat", True), ("z", "abc", False), ("(", "x", False)],
)
def test_subprocess_helper_reports_match_result(
    pattern: str, text: str, expected: bool
) -> None:
    sender = MagicMock()
    _search_regex_in_subprocess(pattern, text, sender)
    sender.send.assert_called_once_with(expected)
    sender.close.assert_called_once()
    assert re is not None


# --- UnitConverterComponent ---


@pytest.fixture
def converter(tk_root: tk.Tk) -> Generator[UnitConverterComponent, None, None]:
    component = UnitConverterComponent(tk_root, MagicMock())
    yield component
    component.destroy()


def _convert(
    component: UnitConverterComponent,
    category: str,
    from_unit: str,
    to_unit: str,
    value: str,
) -> str:
    component.category_var.set(category)
    component._on_category_change()
    component.from_unit_var.set(from_unit)
    component.to_unit_var.set(to_unit)
    component.input_var.set(value)
    component._convert()
    return component.output_var.get()


def test_category_change_populates_units(converter: UnitConverterComponent) -> None:
    converter.category_var.set("Temperature")
    converter._on_category_change()
    assert list(converter.from_unit_combo["values"]) == [
        "Celsius",
        "Fahrenheit",
        "Kelvin",
    ]
    assert converter.from_unit_var.get() == "Celsius"
    assert converter.to_unit_var.get() == "Fahrenheit"


@pytest.mark.parametrize(
    ("from_unit", "to_unit", "value", "expected"),
    [
        ("Celsius", "Celsius", "20", "20.0000"),
        ("Fahrenheit", "Celsius", "212", "100.0000"),
        ("Kelvin", "Celsius", "273.15", "0.0000"),
        ("Celsius", "Kelvin", "0", "273.1500"),
        ("Fahrenheit", "Kelvin", "32", "273.1500"),
        ("Kelvin", "Fahrenheit", "273.15", "32.0000"),
    ],
)
def test_temperature_conversions(
    converter: UnitConverterComponent,
    from_unit: str,
    to_unit: str,
    value: str,
    expected: str,
) -> None:
    assert _convert(converter, "Temperature", from_unit, to_unit, value) == (
        f"Result: {expected}"
    )


def test_weight_conversion(converter: UnitConverterComponent) -> None:
    assert _convert(converter, "Weight", "Kilogram", "Gram", "2") == "Result: 2000.0000"


def test_blank_input_clears_result(converter: UnitConverterComponent) -> None:
    assert _convert(converter, "Length", "Meter", "Foot", "") == "Result:"


def test_too_long_input_is_rejected(converter: UnitConverterComponent) -> None:
    value = "1" * (MAX_CONVERTER_INPUT_LENGTH + 1)
    assert (
        _convert(converter, "Length", "Meter", "Foot", value)
        == "Result: Input too long"
    )


@pytest.mark.parametrize("value", ["abc", "1e999999999999"])
def test_invalid_numbers_are_reported(
    converter: UnitConverterComponent, value: str
) -> None:
    result = _convert(converter, "Length", "Meter", "Foot", value)
    assert result in ("Result: Invalid number", "Result: inf", "Result: Error")


def test_overflowing_conversion_reports_error(
    converter: UnitConverterComponent,
) -> None:
    result = _convert(converter, "Length", "Meter", "Kilometer", "1e308")
    assert result.startswith("Result:")
    converter.conversions["Length"]["Meter"] = 0
    assert _convert_with_zero(converter) == "Result: Error"


def _convert_with_zero(converter: UnitConverterComponent) -> str:
    converter.category_var.set("Length")
    converter.from_unit_var.set("Kilometer")
    converter.to_unit_var.set("Meter")  # 0 で割る
    converter.input_var.set("5")
    converter._convert()
    return converter.output_var.get()


def test_time_conversion_between_same_units_echoes_input(
    converter: UnitConverterComponent,
) -> None:
    assert (
        _convert(converter, "Time", "Unix Timestamp", "Unix Timestamp", "123")
        == "Result: 123"
    )


def test_unix_timestamp_to_datetime(converter: UnitConverterComponent) -> None:
    result = _convert(converter, "Time", "Unix Timestamp", "Datetime String", "86400")
    assert re.fullmatch(r"Result: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result)


@pytest.mark.parametrize("value", ["-1", "253402300800", "not-a-number"])
def test_unix_timestamp_out_of_range_is_an_error(
    converter: UnitConverterComponent, value: str
) -> None:
    assert (
        _convert(converter, "Time", "Unix Timestamp", "Datetime String", value)
        == "Result: Error"
    )


@pytest.mark.parametrize(
    "value",
    [
        "2026-03-01 10:20:30",
        "2026-03-01 10:20",
        "2026-03-01",
        "2026/03/01 10:20:30",
        "2026/03/01 10:20",
        "2026/03/01",
    ],
)
def test_datetime_string_formats_convert_to_timestamp(
    converter: UnitConverterComponent, value: str
) -> None:
    result = _convert(converter, "Time", "Datetime String", "Unix Timestamp", value)
    assert re.fullmatch(r"Result: \d+\.\d+", result)


def test_invalid_datetime_string_is_an_error(converter: UnitConverterComponent) -> None:
    assert (
        _convert(converter, "Time", "Datetime String", "Unix Timestamp", "yesterday")
        == "Result: Error"
    )


@pytest.mark.parametrize(
    ("output", "copied"),
    [
        ("Result: 12.5000", "12.5000"),
        ("Result: Error", None),
        ("Result: Invalid number", None),
        ("Result:", None),
        ("Other text", None),
    ],
)
def test_copy_result_only_copies_valid_values(
    converter: UnitConverterComponent, output: str, copied: str | None
) -> None:
    converter.output_var.set(output)
    converter._copy_result()
    if copied is None:
        converter.app.monitor.update_clipboard.assert_not_called()
    else:
        converter.app.monitor.update_clipboard.assert_called_once_with(copied)
