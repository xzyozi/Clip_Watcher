from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class SourceKind(Enum):
    """テキスト入力の種別"""

    EXPLICIT_TEXT = auto()
    CLIPBOARD = auto()


class ExecutionStatus(Enum):
    """Workflow の実行ステータス"""

    COMPLETED = auto()
    COMPLETED_WITH_WARNING = auto()
    REJECTED = auto()
    FAILED = auto()


@dataclass(frozen=True)
class Classification:
    """分類結果"""

    category_id: str
    matched_rule_id: str | None = None
    confidence: float = 1.0
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowRequest:
    """Workflow 実行要求"""

    request_id: str
    source_kind: SourceKind
    input_text: str
    workspace_root: str | None = None
    category_hint: str | None = None
    template_id: str | None = None
    normalization_profile: str | None = None
    save_history: bool = True
    runtime_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowResult:
    """Workflow 実行結果"""

    request_id: str
    status: ExecutionStatus
    output_text: str | None = None
    classification: Classification | None = None
    applied_template_id: str | None = None
    applied_normalizers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error_message: str | None = None
