from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING

from src.core.text_workflow.models import WorkflowRequest, WorkflowResult
from src.core.text_workflow.workflow import TextWorkflow

if TYPE_CHECKING:
    from src.core.events.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

#: TextWorkflowService が実行結果を通知する既定のイベント種別。
#: EventDispatcher.subscribe(TEXT_WORKFLOW_RESULT_EVENT, listener) で
#: WorkflowResult を受け取れる（DD-003 §5.3）。
TEXT_WORKFLOW_RESULT_EVENT = "TEXT_WORKFLOW_RESULT"


class TextWorkflowService:
    """TextWorkflow を非同期・スレッドプールで提供するサービス。

    ``TextWorkflow.execute()`` はワーカースレッドで実行されるため、実行結果を
    GUI（Tkinter メインスレッド）へ届ける際は、Tkinter の操作をワーカー
    スレッドから直接行わないよう ``ui_thread_marshal`` でメインスレッドへ
    処理を引き渡した上で ``EventDispatcher`` を介して通知する
    （DD-003 §5.3 のスレッド・非同期実行方針）。
    """

    def __init__(
        self,
        workflow: TextWorkflow | None = None,
        max_workers: int = 2,
        event_dispatcher: EventDispatcher | None = None,
        ui_thread_marshal: Callable[[Callable[[], None]], None] | None = None,
        result_event_type: str = TEXT_WORKFLOW_RESULT_EVENT,
    ) -> None:
        """
        Args:
            workflow: 実行対象の TextWorkflow。未指定時は既定構成で生成する。
            max_workers: 実行用スレッドプールの最大ワーカー数。
            event_dispatcher: 指定した場合、実行完了時に
                ``result_event_type`` で ``WorkflowResult`` を dispatch する。
            ui_thread_marshal: ワーカースレッドからメインスレッドへ処理を
                引き渡す関数（例: Tkinter の ``root.after`` を
                ``lambda fn: root.after(0, fn)`` でラップしたもの）。
                未指定の場合、通知はワーカースレッドから直接行われる
                （GUI を持たないテスト・CLI用途向けの既定動作）。
                Tkinter 等の GUI と統合する場合は必ず指定すること。
            result_event_type: dispatch するイベント種別名。
        """
        self._workflow = workflow or TextWorkflow()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="TextWorkflowWorker"
        )
        self._event_dispatcher = event_dispatcher
        self._ui_thread_marshal = ui_thread_marshal
        self._result_event_type = result_event_type

    def execute_async(
        self,
        request: WorkflowRequest,
        callback: Callable[[WorkflowResult], None] | None = None,
    ) -> Future[WorkflowResult]:
        """非同期スレッドで Workflow を実行し、完了後に通知する。

        完了通知（``event_dispatcher.dispatch()`` と ``callback``）は
        ``ui_thread_marshal`` が指定されていればメインスレッドへ引き渡した
        上で実行され、未指定の場合は完了したワーカースレッドから直接実行される。
        """
        future = self._executor.submit(self._workflow.execute, request)
        future.add_done_callback(lambda f: self._on_task_done(f, callback=callback))
        return future

    def _on_task_done(
        self,
        future: Future[WorkflowResult],
        callback: Callable[[WorkflowResult], None] | None,
    ) -> None:
        """ワーカースレッド側で呼ばれる完了コールバック（内部専用）。

        ここでは結果の取得のみを行い、実際の通知（EventDispatcher.dispatch /
        callback 呼び出し）は ``_deliver_result()`` に委譲してメインスレッドへ
        引き渡す。
        """
        try:
            result = future.result()
        except Exception:
            logger.exception("TextWorkflow の非同期実行中に例外が発生しました")
            return

        self._deliver_result(result, callback)

    def _deliver_result(
        self,
        result: WorkflowResult,
        callback: Callable[[WorkflowResult], None] | None,
    ) -> None:
        """実行結果を通知する。``ui_thread_marshal`` があればメインスレッドへ
        処理を引き渡してから通知する。
        """

        def _notify() -> None:
            if self._event_dispatcher is not None:
                self._event_dispatcher.dispatch(self._result_event_type, result)
            if callback:
                callback(result)

        if self._ui_thread_marshal is not None:
            self._ui_thread_marshal(_notify)
        else:
            _notify()

    def shutdown(self) -> None:
        """サービス停止時のスレッドクリーンアップ"""
        self._executor.shutdown(wait=False)
