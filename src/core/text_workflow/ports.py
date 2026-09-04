"""TextWorkflow が外部実装に要求する最小 Interface。"""

from __future__ import annotations

from typing import Any, Protocol

from src.core.text_workflow.history import HistoryEntry


class WorkflowConfiguration(Protocol):
    """実行時設定を解決する Interface。"""

    def resolve(
        self,
        runtime_overrides: dict[str, Any] | None = None,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        """実行要求に適用する設定を返す。"""
        ...


class ExecutionHistoryRecorder(Protocol):
    """Workflow 実行履歴を記録する Interface。"""

    def record(self, entry: HistoryEntry) -> bool:
        """履歴を記録し、成功時は ``True`` を返す。"""
        ...
