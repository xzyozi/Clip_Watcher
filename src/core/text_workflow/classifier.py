from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.core.text_workflow.models import Classification


class Classifier:
    """テキストをルールに基づいて自動分類するモジュール"""

    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None, default_category: str = "general") -> None:
        self._rules = rules or []
        self._default_category = default_category

    def classify(self, text: str, category_hint: Optional[str] = None) -> Classification:
        """
        テキストを分類する。
        category_hint が指定された場合は優先して採用する。
        それ以外は定義されたルールを優先度昇順に評価する。
        """
        if category_hint:
            return Classification(category_id=category_hint, confidence=1.0, tags=["hinted"])

        # priority 昇順、id 昇順でソート
        sorted_rules = sorted(
            [r for r in self._rules if r.get("enabled", True)],
            key=lambda r: (r.get("priority", 100), r.get("id", ""))
        )

        for rule in sorted_rules:
            when = rule.get("when", {})
            if self._evaluate_condition(when, text):
                return Classification(
                    category_id=rule.get("categoryId", self._default_category),
                    matched_rule_id=rule.get("id"),
                    confidence=1.0,
                    tags=rule.get("tags", []),
                )

        return Classification(category_id=self._default_category, confidence=0.0)

    def _evaluate_condition(self, condition: Dict[str, Any], text: str) -> bool:
        """単一または複合条件を評価する"""
        if not condition:
            return False

        # 論理積 (all)
        if "all" in condition:
            return all(self._evaluate_condition(c, text) for c in condition["all"])

        # 論理和 (any)
        if "any" in condition:
            return any(self._evaluate_condition(c, text) for c in condition["any"])

        # 否定 (not)
        if "not" in condition:
            return not self._evaluate_condition(condition["not"], text)

        # 個別判定 (kind)
        kind = condition.get("kind")
        if kind == "contains":
            val = condition.get("value", "")
            return val in text if val else False

        if kind == "containsAny":
            values = condition.get("values", [])
            return any(v in text for v in values)

        if kind == "regex":
            pattern = condition.get("pattern", "")
            if not pattern:
                return False
            try:
                return bool(re.search(pattern, text))
            except re.error:
                return False

        if kind == "minLength":
            val = int(condition.get("value", 0))
            return bool(len(text) >= val)

        if kind == "maxLength":
            val = float(condition.get("value", float("inf")))
            return bool(len(text) <= val)

        return False
