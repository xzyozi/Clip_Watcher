"""TextWorkflow の公開 Interface。

互換性ポリシー・公開範囲の正本は
docs/design/CLW-DD-003_TextWorkflow詳細設計書.md の
「公開Interfaceと互換性ポリシー」章を参照する。

ここで `__all__` に列挙するシンボルのみが公開 Interface であり、
それ以外のサブモジュール（classifier, normalizer, template_renderer 等）
は内部実装として予告なく変更されうる。
"""

from src.core.text_workflow.errors import TextWorkflowError
from src.core.text_workflow.models import (
    Classification,
    ExecutionStatus,
    SourceKind,
    WorkflowRequest,
    WorkflowResult,
)
from src.core.text_workflow.workflow import TextWorkflow

__all__ = [
    "SourceKind",
    "ExecutionStatus",
    "Classification",
    "WorkflowRequest",
    "WorkflowResult",
    "TextWorkflow",
    "TextWorkflowError",
]
