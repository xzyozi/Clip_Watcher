from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


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
    matched_rule_id: Optional[str] = None
    confidence: float = 1.0
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowRequest:
    """Workflow 実行要求"""
    request_id: str
    source_kind: SourceKind
    input_text: str
    workspace_root: Optional[str] = None
    category_hint: Optional[str] = None
    template_id: Optional[str] = None
    normalization_profile: Optional[str] = None
    save_history: bool = True
    runtime_overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowResult:
    """Workflow 実行結果"""
    request_id: str
    status: ExecutionStatus
    output_text: Optional[str] = None
    classification: Optional[Classification] = None
    applied_template_id: Optional[str] = None
    applied_normalizers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
