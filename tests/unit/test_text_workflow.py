from __future__ import annotations

import json
import os
import tempfile
import unittest
import uuid

from src.core.text_workflow.classifier import Classifier
from src.core.text_workflow.config_resolver import ConfigurationResolver, deep_overlay
from src.core.text_workflow.history import ExecutionHistory, HistoryEntry
from src.core.text_workflow.models import (
    ExecutionStatus,
    SourceKind,
    WorkflowRequest,
)
from src.core.text_workflow.normalizer import Normalizer
from src.core.text_workflow.template_renderer import TemplateRenderer
from src.core.text_workflow.workflow import TextWorkflow
from src.services.text_workflow_service import (
    TEXT_WORKFLOW_RESULT_EVENT,
    TextWorkflowService,
)


class TestTextWorkflowUnit(unittest.TestCase):
    def test_deep_overlay(self) -> None:
        base = {"a": 1, "b": {"c": 2, "d": 3}, "list": [1, 2]}
        overlay = {"b": {"d": 4}, "list": [3]}
        res = deep_overlay(base, overlay)
        self.assertEqual(res["a"], 1)
        self.assertEqual(res["b"]["c"], 2)
        self.assertEqual(res["b"]["d"], 4)
        self.assertEqual(res["list"], [3])

    def test_classifier_rules(self) -> None:
        rules = [
            {
                "id": "meeting-rule",
                "priority": 10,
                "categoryId": "meeting",
                "when": {
                    "all": [
                        {"kind": "contains", "value": "議事録"},
                        {"kind": "containsAny", "values": ["日時", "アジェンダ"]},
                    ]
                },
            },
            {
                "id": "url-rule",
                "priority": 5,
                "categoryId": "url",
                "when": {"kind": "regex", "pattern": r"^https?://"},
            },
        ]
        classifier = Classifier(rules=rules, default_category="general")

        # URL判定 (priority: 5 が優先)
        res1 = classifier.classify("https://example.com")
        self.assertEqual(res1.category_id, "url")
        self.assertEqual(res1.matched_rule_id, "url-rule")

        # 議事録判定
        res2 = classifier.classify("本日の議事録です。\n日時: 2026-08-04")
        self.assertEqual(res2.category_id, "meeting")
        self.assertEqual(res2.matched_rule_id, "meeting-rule")

        # 該当なし
        res3 = classifier.classify("普通のメモテキスト")
        self.assertEqual(res3.category_id, "general")
        self.assertIsNone(res3.matched_rule_id)

    def test_classifier_regex_rejects_overlong_pattern(self) -> None:
        """ReDoS対策: パターン長が上限を超える regex ルールは拒否され、
        マッチしない（例外にもならない）ことを確認する（DD-003 §7）。"""
        overlong_pattern = "(a+)+" + "b" * 300  # 300文字超のパターン
        rules = [
            {
                "id": "overlong-rule",
                "priority": 1,
                "categoryId": "matched",
                "when": {"kind": "regex", "pattern": overlong_pattern},
            }
        ]
        classifier = Classifier(
            rules=rules, default_category="general", regex_max_pattern_length=200
        )
        result = classifier.classify("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!")
        # パターンが拒否されるため、ルールにはマッチせず既定カテゴリになる。
        self.assertEqual(result.category_id, "general")
        self.assertIsNone(result.matched_rule_id)

    def test_classifier_regex_times_out_on_catastrophic_backtracking(self) -> None:
        """ReDoS対策: 破滅的バックトラックを起こすパターンでも、
        タイムアウト時間内に処理が返り、呼び出し元をブロックしないことを
        確認する（DD-003 §7）。"""
        # (a+)+ は 'a' の連続 + 末尾に非マッチ文字を含む入力で
        # 指数的バックトラックを起こす典型的なReDoSパターン。
        catastrophic_pattern = r"(a+)+$"
        rules = [
            {
                "id": "catastrophic-rule",
                "priority": 1,
                "categoryId": "matched",
                "when": {"kind": "regex", "pattern": catastrophic_pattern},
            }
        ]
        classifier = Classifier(
            rules=rules,
            default_category="general",
            regex_timeout_seconds=0.2,
        )
        malicious_input = "a" * 40 + "!"

        import time

        start = time.monotonic()
        result = classifier.classify(malicious_input)
        elapsed = time.monotonic() - start

        # タイムアウト（0.2秒）程度で処理が返ってくること。
        # 素朴な実装では数秒〜数十秒かかるため、大幅なマージンを取って検証する。
        self.assertLess(elapsed, 2.0)
        self.assertEqual(result.category_id, "general")
        self.assertIsNone(result.matched_rule_id)

    def test_classifier_regex_normal_pattern_still_matches(self) -> None:
        """ReDoS対策導入後も、通常のregexパターンは正しくマッチすることを
        確認する（回帰防止）。"""
        rules = [
            {
                "id": "url-rule",
                "priority": 1,
                "categoryId": "url",
                "when": {"kind": "regex", "pattern": r"^https?://"},
            }
        ]
        classifier = Classifier(rules=rules, default_category="general")
        result = classifier.classify("https://example.com")
        self.assertEqual(result.category_id, "url")
        self.assertEqual(result.matched_rule_id, "url-rule")

    def test_template_renderer(self) -> None:
        templates = [
            {
                "id": "meeting-summary",
                "body": "## {{category}}\n{{input}}\nDate: {{date}}",
                "variables": [{"name": "input", "required": True}],
            }
        ]
        renderer = TemplateRenderer(templates=templates)
        out = renderer.render(
            template_id="meeting-summary",
            variables={"input": "内容テスト", "category": "meeting"},
        )
        self.assertIn("## meeting", out)
        self.assertIn("内容テスト", out)

    def test_normalizer_idempotence(self) -> None:
        normalizer = Normalizer()
        raw_text = "line1 \r\nline2\t\r\n"
        norm1, _ = normalizer.normalize(raw_text, profile_name="plain")
        norm2, _ = normalizer.normalize(norm1, profile_name="plain")
        self.assertEqual(norm1, norm2)
        self.assertEqual(norm1, "line1\nline2\n")

    def test_execution_history(self) -> None:
        history = ExecutionHistory(db_path=":memory:", max_records=2)
        entry1 = HistoryEntry(
            record_id="rec1",
            request_id="req1",
            category_id="general",
            rule_id=None,
            template_id="plain",
            input_text="in1",
            output_text="out1",
            created_at="2026-08-04T10:00:00",
        )
        entry2 = HistoryEntry(
            record_id="rec2",
            request_id="req2",
            category_id="meeting",
            rule_id="m1",
            template_id="m-tpl",
            input_text="in2",
            output_text="out2",
            created_at="2026-08-04T10:01:00",
        )
        entry3 = HistoryEntry(
            record_id="rec3",
            request_id="req3",
            category_id="url",
            rule_id="u1",
            template_id="u-tpl",
            input_text="in3",
            output_text="out3",
            created_at="2026-08-04T10:02:00",
        )

        history.record(entry1)
        history.record(entry2)
        history.record(entry3)

        recent = history.get_recent(limit=10)
        self.assertEqual(len(recent), 2)
        rec_ids = [r.record_id for r in recent]
        self.assertNotIn("rec1", rec_ids)  # rec1 は上限2件のためパージされた
        self.assertIn("rec2", rec_ids)
        self.assertIn("rec3", rec_ids)

    def test_full_text_workflow_pipeline(self) -> None:
        builtin_config = {
            "workflow": {
                "defaultCategory": "general",
                "maxInputBytes": 1000,
                "defaultTemplateId": "plain",
            },
            "rules": [
                {
                    "id": "meeting-rule",
                    "priority": 1,
                    "categoryId": "meeting",
                    "templateId": "meeting-tpl",
                    "when": {"kind": "contains", "value": "議事録"},
                }
            ],
            "templates": [
                {
                    "id": "meeting-tpl",
                    "body": "[要約]\n{{input}}",
                }
            ],
        }

        resolver = ConfigurationResolver(builtin_config=builtin_config)
        history = ExecutionHistory(db_path=":memory:")
        workflow = TextWorkflow(config_resolver=resolver, history=history)

        request = WorkflowRequest(
            request_id=str(uuid.uuid4()),
            source_kind=SourceKind.EXPLICIT_TEXT,
            input_text="本日の議事録メモです \r\n",
            save_history=True,
        )

        result = workflow.execute(request)
        self.assertEqual(result.status, ExecutionStatus.COMPLETED)
        self.assertEqual(result.classification.category_id, "meeting")
        self.assertEqual(result.output_text, "[要約]\n本日の議事録メモです\n")

        # 履歴件数の確認
        history_records = history.get_recent(limit=5)
        self.assertEqual(len(history_records), 1)
        self.assertEqual(
            history_records[0].output_text, "[要約]\n本日の議事録メモです\n"
        )

    def test_workflow_input_too_large(self) -> None:
        builtin_config = {"workflow": {"maxInputBytes": 10}}
        workflow = TextWorkflow(
            config_resolver=ConfigurationResolver(builtin_config=builtin_config)
        )

        request = WorkflowRequest(
            request_id="req-large",
            source_kind=SourceKind.EXPLICIT_TEXT,
            input_text="123456789012345",  # 15 bytes
        )
        result = workflow.execute(request)
        self.assertEqual(result.status, ExecutionStatus.REJECTED)
        self.assertIn("exceeds limit", result.error_message or "")

    def test_async_workflow_service(self) -> None:
        service = TextWorkflowService()
        req = WorkflowRequest(
            request_id="async-req",
            source_kind=SourceKind.EXPLICIT_TEXT,
            input_text="テスト非同期",
            save_history=False,
        )
        future = service.execute_async(req)
        res = future.result(timeout=2.0)
        self.assertEqual(res.status, ExecutionStatus.COMPLETED)
        self.assertEqual(res.output_text, "テスト非同期")
        service.shutdown()

    def test_config_resolver_from_app_data_dir_loads_user_config(self) -> None:
        """ConfigurationResolver.from_app_data_dir() が実ファイルの
        workflow.json をユーザー設定として読み込むことを確認する。"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "workflow.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"workflow": {"defaultCategory": "custom"}}, f)

            resolver = ConfigurationResolver.from_app_data_dir(tmp_dir)
            resolved = resolver.resolve()
            self.assertEqual(resolved["workflow"]["defaultCategory"], "custom")

    def test_config_resolver_from_app_data_dir_missing_file_uses_defaults(
        self,
    ) -> None:
        """workflow.json が存在しない場合、組み込み既定値のみが使われる。"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolver = ConfigurationResolver.from_app_data_dir(tmp_dir)
            resolved = resolver.resolve()
            self.assertEqual(resolved["workflow"]["defaultCategory"], "general")

    def test_config_resolver_resolves_workspace_root_dynamically(self) -> None:
        """resolve() に workspace_root を渡すと、
        {workspace_root}/.clipwatcher/workflow.json が動的に読み込まれる。"""
        with tempfile.TemporaryDirectory() as workspace_root:
            workspace_config_dir = os.path.join(workspace_root, ".clipwatcher")
            os.makedirs(workspace_config_dir)
            config_path = os.path.join(workspace_config_dir, "workflow.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"workflow": {"defaultCategory": "workspace-scoped"}}, f)

            resolver = ConfigurationResolver()
            resolved = resolver.resolve(workspace_root=workspace_root)
            self.assertEqual(
                resolved["workflow"]["defaultCategory"], "workspace-scoped"
            )

    def test_workflow_uses_request_workspace_root(self) -> None:
        """TextWorkflow.execute() が WorkflowRequest.workspace_root を
        ConfigurationResolver.resolve() に伝播させることを確認する。"""
        with tempfile.TemporaryDirectory() as workspace_root:
            workspace_config_dir = os.path.join(workspace_root, ".clipwatcher")
            os.makedirs(workspace_config_dir)
            config_path = os.path.join(workspace_config_dir, "workflow.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"workflow": {"maxInputBytes": 5}}, f)

            workflow = TextWorkflow(config_resolver=ConfigurationResolver())
            request = WorkflowRequest(
                request_id="req-workspace",
                source_kind=SourceKind.EXPLICIT_TEXT,
                input_text="123456789012345",  # 15 bytes > maxInputBytes=5
                workspace_root=workspace_root,
                save_history=False,
            )
            result = workflow.execute(request)
            self.assertEqual(result.status, ExecutionStatus.REJECTED)
            self.assertIn("exceeds limit", result.error_message or "")

    def test_service_notifies_via_event_dispatcher_through_ui_thread_marshal(
        self,
    ) -> None:
        """TextWorkflowService が EventDispatcher 経由で結果を通知する際、
        通知処理が ui_thread_marshal を経由して実行されることを確認する
        （ワーカースレッドから直接 dispatch しないことの検証、DD-003 §5.3）。"""
        dispatched: list[object] = []
        marshalled_calls: list[object] = []

        class FakeEventDispatcher:
            def dispatch(self, event_type: str, payload: object) -> None:
                dispatched.append((event_type, payload))

        def fake_marshal(fn: object) -> None:
            marshalled_calls.append(fn)
            fn()  # type: ignore[operator]

        service = TextWorkflowService(
            event_dispatcher=FakeEventDispatcher(),  # type: ignore[arg-type]
            ui_thread_marshal=fake_marshal,
        )
        req = WorkflowRequest(
            request_id="ui-marshal-req",
            source_kind=SourceKind.EXPLICIT_TEXT,
            input_text="通知テスト",
            save_history=False,
        )
        future = service.execute_async(req)
        future.result(timeout=2.0)

        # 完了コールバックはスレッドプール内で非同期に呼ばれるため、
        # 通知が届くまで待機する。
        import time

        for _ in range(50):
            if dispatched:
                break
            time.sleep(0.02)

        self.assertEqual(len(marshalled_calls), 1)
        self.assertEqual(len(dispatched), 1)
        event_type, result = dispatched[0]
        self.assertEqual(event_type, TEXT_WORKFLOW_RESULT_EVENT)
        self.assertEqual(result.status, ExecutionStatus.COMPLETED)  # type: ignore[attr-defined]
        service.shutdown()


if __name__ == "__main__":
    unittest.main()
