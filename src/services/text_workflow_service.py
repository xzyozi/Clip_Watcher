from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Optional

from src.core.text_workflow.models import WorkflowRequest, WorkflowResult
from src.core.text_workflow.workflow import TextWorkflow


class TextWorkflowService:
    """TextWorkflow を非同期・スレッドプールで提供するサービス"""

    def __init__(self, workflow: Optional[TextWorkflow] = None, max_workers: int = 2) -> None:
        self._workflow = workflow or TextWorkflow()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="TextWorkflowWorker")

    def execute_async(
        self,
        request: WorkflowRequest,
        callback: Optional[Callable[[WorkflowResult], None]] = None
    ) -> Future[WorkflowResult]:
        """非同期スレッドで Workflow を実行し、完了後に callback を起動する"""
        future = self._executor.submit(self._workflow.execute, request)

        if callback:
            def _done_callback(f: Future[WorkflowResult]) -> None:
                try:
                    result = f.result()
                    callback(result)
                except Exception as e:
                    # 例外発生時のフォールバック処理
                    pass

            future.add_done_callback(_done_callback)

        return future

    def shutdown(self) -> None:
        """サービス停止時のスレッドクリーンアップ"""
        self._executor.shutdown(wait=False)
