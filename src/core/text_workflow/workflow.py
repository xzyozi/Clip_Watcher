from __future__ import annotations

import uuid
from datetime import datetime

from src.core.text_workflow.classifier import Classifier
from src.core.text_workflow.config_resolver import ConfigurationResolver
from src.core.text_workflow.errors import TextWorkflowError
from src.core.text_workflow.history import ExecutionHistory, HistoryEntry
from src.core.text_workflow.models import (
    ExecutionStatus,
    WorkflowRequest,
    WorkflowResult,
)
from src.core.text_workflow.normalizer import Normalizer
from src.core.text_workflow.template_renderer import TemplateRenderer


class TextWorkflow:
    """Text Workflow のメインオーケストレーター"""

    def __init__(
        self,
        config_resolver: ConfigurationResolver | None = None,
        history: ExecutionHistory | None = None,
    ) -> None:
        self._config_resolver = config_resolver or ConfigurationResolver()
        self._history = history or ExecutionHistory(":memory:")

    def execute(self, request: WorkflowRequest) -> WorkflowResult:
        """単一の WorkflowRequest を受領し、WorkflowResult を返す"""
        warnings: list[str] = []

        # 1. 設定の解決
        config = self._config_resolver.resolve(request.runtime_overrides)
        wf_config = config.get("workflow", {})

        # 2. 入力制限チェック
        max_bytes = wf_config.get("maxInputBytes", 1048576)
        if len(request.input_text.encode("utf-8")) > max_bytes:
            return WorkflowResult(
                request_id=request.request_id,
                status=ExecutionStatus.REJECTED,
                error_message=f"Input size exceeds limit of {max_bytes} bytes",
            )

        # 3. 分類 (Classifier)
        rules = config.get("rules", [])
        default_category = wf_config.get("defaultCategory", "general")
        classifier = Classifier(rules=rules, default_category=default_category)
        classification = classifier.classify(
            request.input_text, category_hint=request.category_hint
        )

        # 4. テンプレート展開 (TemplateRenderer)
        templates = config.get("templates", [])
        template_renderer = TemplateRenderer(templates=templates)
        target_template_id = (
            request.template_id
            or (
                classification.matched_rule_id
                and next(
                    (
                        r.get("templateId")
                        for r in rules
                        if r.get("id") == classification.matched_rule_id
                    ),
                    None,
                )
            )
            or wf_config.get("defaultTemplateId")
        )

        template_vars = {
            "input": request.input_text,
            "category": classification.category_id,
            "tags": ", ".join(classification.tags),
        }

        try:
            rendered_text = template_renderer.render(
                template_id=target_template_id,
                variables=template_vars,
                default_body=request.input_text,
            )
        except TextWorkflowError as e:
            # 内部コンポーネント (Classifier/TemplateRenderer/Normalizer 等) が
            # 発生させる TextWorkflowError 系の例外はここで一括して捕捉し、
            # 呼び出し側へは例外を伝播させず WorkflowResult (REJECTED) に変換する。
            return WorkflowResult(
                request_id=request.request_id,
                status=ExecutionStatus.REJECTED,
                error_message=str(e),
            )

        # 5. 正規化 (Normalizer)
        profiles = wf_config.get("normalizationProfiles", {})
        normalizer = Normalizer(custom_profiles=profiles)
        profile_name = request.normalization_profile or "plain"
        normalized_text, applied_normalizers = normalizer.normalize(
            rendered_text, profile_name=profile_name
        )

        status = ExecutionStatus.COMPLETED

        # 6. 履歴保存
        if request.save_history:
            history_entry = HistoryEntry(
                record_id=str(uuid.uuid4()),
                request_id=request.request_id,
                category_id=classification.category_id,
                rule_id=classification.matched_rule_id,
                template_id=target_template_id,
                input_text=request.input_text,
                output_text=normalized_text,
                created_at=datetime.now().isoformat(),
            )
            saved = self._history.record(history_entry)
            if not saved:
                status = ExecutionStatus.COMPLETED_WITH_WARNING
                warnings.append("Failed to record execution history to private store")

        return WorkflowResult(
            request_id=request.request_id,
            status=status,
            output_text=normalized_text,
            classification=classification,
            applied_template_id=target_template_id,
            applied_normalizers=applied_normalizers,
            warnings=warnings,
        )
