from __future__ import annotations

import logging
import multiprocessing
import re
from multiprocessing.connection import Connection
from typing import Any

from src.core.text_workflow.models import Classification

logger = logging.getLogger(__name__)

#: ReDoS対策（DD-003 §7）の既定値。
#: ConfigurationResolver 側の既定値（config_resolver.DEFAULT_BUILTIN_CONFIG）
#: と同じ値を、Classifier を config 抜きで直接利用するケース向けに保持する。
DEFAULT_REGEX_MAX_PATTERN_LENGTH = 200
DEFAULT_REGEX_TIMEOUT_SECONDS = 0.5


def _search_regex_in_subprocess(
    pattern: str, text: str, result_sender: Connection
) -> None:
    """子プロセスで正規表現を評価し、結果を親プロセスへ返す（内部専用）。"""
    try:
        result_sender.send(bool(re.search(pattern, text)))
    except re.error:
        result_sender.send(False)
    finally:
        result_sender.close()


class Classifier:
    """テキストをルールに基づいて自動分類するモジュール"""

    def __init__(
        self,
        rules: list[dict[str, Any]] | None = None,
        default_category: str = "general",
        regex_max_pattern_length: int = DEFAULT_REGEX_MAX_PATTERN_LENGTH,
        regex_timeout_seconds: float = DEFAULT_REGEX_TIMEOUT_SECONDS,
    ) -> None:
        self._rules = rules or []
        self._default_category = default_category
        self._regex_max_pattern_length = (
            regex_max_pattern_length
            if isinstance(regex_max_pattern_length, int)
            and not isinstance(regex_max_pattern_length, bool)
            and regex_max_pattern_length > 0
            else DEFAULT_REGEX_MAX_PATTERN_LENGTH
        )
        self._regex_timeout_seconds = (
            float(regex_timeout_seconds)
            if isinstance(regex_timeout_seconds, (int, float))
            and not isinstance(regex_timeout_seconds, bool)
            and regex_timeout_seconds > 0
            else DEFAULT_REGEX_TIMEOUT_SECONDS
        )

    def classify(self, text: str, category_hint: str | None = None) -> Classification:
        """
        テキストを分類する。
        category_hint が指定された場合は優先して採用する。
        それ以外は定義されたルールを優先度昇順に評価する。
        """
        if category_hint:
            return Classification(
                category_id=category_hint, confidence=1.0, tags=["hinted"]
            )

        # priority 昇順、id 昇順でソート
        sorted_rules = sorted(
            [r for r in self._rules if r.get("enabled", True)],
            key=lambda r: (r.get("priority", 100), r.get("id", "")),
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

    def _evaluate_condition(self, condition: dict[str, Any], text: str) -> bool:
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
            return self._evaluate_regex_safely(pattern, text)

        if kind == "minLength":
            val = int(condition.get("value", 0))
            return bool(len(text) >= val)

        if kind == "maxLength":
            val = float(condition.get("value", float("inf")))
            return bool(len(text) <= val)

        return False

    def _evaluate_regex_safely(self, pattern: str, text: str) -> bool:
        """ReDoS対策（DD-003 §7）を適用した上で正規表現マッチを評価する。

        1. パターン長制限: ``regex_max_pattern_length`` を超えるパターンは
           コンパイル前に拒否する（静的かつ確実な一次防御）。
        2. 実行時間制限: ``multiprocessing`` の子プロセスで ``re.search()`` を
           実行する。``regex_timeout_seconds`` を超えた子プロセスは
           ``terminate()`` で強制終了し、False（マッチなし）を返す。

        CPython標準の ``re`` はバックトラック中にGILを解放せず、スレッドでは
        安全なタイムアウトを実現できない。そのため、強制終了可能な別プロセスへ
        隔離する。Windowsでも動く ``spawn`` コンテキストを明示的に使用する。
        各regex評価でプロセス起動コストが発生するため、分類ルールのregex利用は
        必要最小限に留めること。
        """
        if len(pattern) > self._regex_max_pattern_length:
            logger.warning(
                "分類ルールのregexパターンが上限(%d文字)を超えたため拒否しました: "
                "pattern_length=%d",
                self._regex_max_pattern_length,
                len(pattern),
            )
            return False

        try:
            re.compile(pattern)
        except re.error:
            return False

        context = multiprocessing.get_context("spawn")
        result_receiver, result_sender = context.Pipe(duplex=False)
        process = context.Process(
            target=_search_regex_in_subprocess,
            args=(pattern, text, result_sender),
            daemon=True,
        )

        try:
            process.start()
            # 子プロセス側だけが使用する送信側パイプを親から閉じる。
            result_sender.close()
            process.join(timeout=self._regex_timeout_seconds)

            if process.is_alive():
                process.terminate()
                process.join()
                logger.warning(
                    "分類ルールのregex実行が%s秒を超えたため子プロセスを終了しました "
                    "（ReDoSの可能性、DD-003 §7）: pattern=%r",
                    self._regex_timeout_seconds,
                    pattern,
                )
                return False

            if result_receiver.poll():
                return bool(result_receiver.recv())
            return False
        finally:
            result_sender.close()
            result_receiver.close()
            # Process.close() は終了済みプロセスのOSリソースを解放する。
            if not process.is_alive():
                process.close()
