"""tests/unit/test_classifier_robustness.py

Classifier の正規表現評価で、子プロセスが異常終了しても例外が呼び出し元へ
伝播せず、マッチなしとして分類が継続されることを検証する (#113)。
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.text_workflow.classifier import Classifier


def _fake_context(receiver: MagicMock) -> MagicMock:
    process = MagicMock()
    process.is_alive.return_value = False
    sender = MagicMock()
    context = MagicMock()
    context.Pipe.return_value = (receiver, sender)
    context.Process.return_value = process
    return context


@pytest.mark.parametrize("error", [EOFError(), OSError("broken pipe")])
def test_regex_returns_false_when_child_process_dies_before_sending(
    error: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    receiver = MagicMock()
    receiver.poll.return_value = True
    receiver.recv.side_effect = error
    classifier = Classifier(default_category="general")

    with (
        patch("multiprocessing.get_context", return_value=_fake_context(receiver)),
        caplog.at_level(logging.WARNING),
    ):
        matched = classifier._evaluate_regex_safely("abc", "abc")

    assert matched is False
    assert any("異常終了" in r.getMessage() for r in caplog.records)
    receiver.close.assert_called_once()


def test_classify_continues_to_next_rule_after_child_process_failure() -> None:
    """regex ルールで子プロセスが落ちても、後続ルールの評価とフォールバックが続く。"""
    receiver = MagicMock()
    receiver.poll.return_value = True
    receiver.recv.side_effect = EOFError()
    rules: list[dict[str, Any]] = [
        {
            "id": "r1",
            "priority": 1,
            "categoryId": "regexed",
            "when": {"kind": "regex", "pattern": "abc"},
        },
        {
            "id": "r2",
            "priority": 2,
            "categoryId": "plain",
            "when": {"kind": "contains", "value": "abc"},
        },
    ]
    classifier = Classifier(rules=rules)

    with patch("multiprocessing.get_context", return_value=_fake_context(receiver)):
        result = classifier.classify("abc")

    assert result.category_id == "plain"
    assert result.matched_rule_id == "r2"


def test_regex_normal_path_still_returns_child_result() -> None:
    receiver = MagicMock()
    receiver.poll.return_value = True
    receiver.recv.return_value = True
    classifier = Classifier()

    with patch("multiprocessing.get_context", return_value=_fake_context(receiver)):
        assert classifier._evaluate_regex_safely("abc", "abc") is True
