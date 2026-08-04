from __future__ import annotations

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
from src.core.text_workflow.template_renderer import TemplateError, TemplateRenderer
from src.core.text_workflow.workflow import TextWorkflow
from src.services.text_workflow_service import TextWorkflowService


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
        self.assertEqual(history_records[0].output_text, "[要約]\n本日の議事録メモです\n")

    def test_workflow_input_too_large(self) -> None:
        builtin_config = {"workflow": {"maxInputBytes": 10}}
        workflow = TextWorkflow(config_resolver=ConfigurationResolver(builtin_config=builtin_config))

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


if __name__ == "__main__":
    unittest.main()
