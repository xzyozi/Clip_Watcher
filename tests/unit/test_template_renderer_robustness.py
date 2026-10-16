"""tests/unit/test_template_renderer_robustness.py

TemplateRenderer が None や不正なデータ型を含むテンプレート定義でも
TypeError で落ちず、安全な値にフォールバックすることを検証する (#114)。
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core.text_workflow.errors import TextWorkflowError
from src.core.text_workflow.template_renderer import TemplateRenderer


def _render(template: dict[str, Any], variables: dict[str, Any] | None = None) -> str:
    renderer = TemplateRenderer([{"id": "t", **template}])
    return renderer.render("t", variables or {"input": "x"})


def test_null_body_renders_empty_string() -> None:
    assert _render({"body": None}) == ""


@pytest.mark.parametrize("body", [123, ["a"], {"k": "v"}])
def test_non_string_body_renders_empty_string(body: object) -> None:
    assert _render({"body": body}) == ""


def test_null_variables_definition_is_treated_as_empty() -> None:
    assert _render({"body": "{{input}}", "variables": None}) == "x"


def test_non_dict_variable_definitions_are_skipped() -> None:
    result = _render(
        {"body": "{{a}}", "variables": ["bad", 1, None, {"name": "a", "default": "D"}]}
    )

    assert result == "D"


def test_none_variable_value_renders_empty_not_literal_none() -> None:
    assert _render({"body": "[{{v}}]"}, {"v": None}) == "[]"


def test_none_default_value_renders_empty() -> None:
    result = _render(
        {"body": "[{{v}}]", "variables": [{"name": "v", "default": None}]}, {}
    )

    assert result == "[]"


def test_undefined_placeholder_is_kept_as_is() -> None:
    assert _render({"body": "{{unknown}}"}) == "{{unknown}}"


def test_non_dict_template_entries_are_ignored() -> None:
    renderer = TemplateRenderer([None, 1, "x", {"id": "ok", "body": "B"}])  # type: ignore[list-item]

    assert renderer.render("ok", {}) == "B"


def test_required_variable_still_raises() -> None:
    template = {
        "body": "{{a}}",
        "variables": [{"name": "a", "required": True}],
    }

    with pytest.raises(TextWorkflowError):
        _render(template, {"a": None})
