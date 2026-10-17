from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import TYPE_CHECKING

from src.core.text_workflow.models import (
    ExecutionStatus,
    WorkflowRequest,
    WorkflowResult,
)
from src.core.text_workflow.workflow import TextWorkflow

if TYPE_CHECKING:
    from src.core.events.event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

#: TextWorkflowService が実行結果を通知する既定のイベント種別。
#: EventDispatcher.subscribe(TEXT_WORKFLOW_RESULT_EVENT, listener) で
#: WorkflowResult を受け取れる（DD-003 §5.3）。
TEXT_WORKFLOW_RESULT_EVENT = "TEXT_WORKFLOW_RESULT"

#: shutdown() が実行中・待機中のタスクの完了を待つ既定の最大秒数。
DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 2.0

_SHUTDOWN_REJECT_MESSAGE = "TextWorkflowService is shut down"


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
        # shutdown 判定と実行中タスクの管理（submit と shutdown の競合を防ぐ）
        self._lock = threading.Lock()
        self._is_shutdown = False
        self._inflight: set[Future[WorkflowResult]] = set()

    def execute_async(
        self,
        request: WorkflowRequest,
        callback: Callable[[WorkflowResult], None] | None = None,
    ) -> Future[WorkflowResult]:
        """非同期スレッドで Workflow を実行し、完了後に通知する。

        完了通知（``event_dispatcher.dispatch()`` と ``callback``）は
        ``ui_thread_marshal`` が指定されていればメインスレッドへ引き渡した
        上で実行され、未指定の場合は完了したワーカースレッドから直接実行される。

        ``shutdown()`` 後に呼ばれた場合は実行せず、``REJECTED`` の結果を持つ
        完了済み Future を返し、同じ経路で完了通知を行う。
        """
        with self._lock:
            if self._is_shutdown:
                future: Future[WorkflowResult] = Future()
                future.set_result(
                    WorkflowResult(
                        request_id=request.request_id,
                        status=ExecutionStatus.REJECTED,
                        error_message=_SHUTDOWN_REJECT_MESSAGE,
                    )
                )
            else:
                future = self._executor.submit(self._workflow.execute, request)
                self._inflight.add(future)

        def _finish(f: Future[WorkflowResult]) -> None:
            with self._lock:
                self._inflight.discard(f)
            self._on_task_done(f, callback=callback, request_id=request.request_id)

        # 完了済みの Future では、この呼び出しスレッドで直ちに _finish が実行される
        future.add_done_callback(_finish)
        return future

    def _on_task_done(
        self,
        future: Future[WorkflowResult],
        callback: Callable[[WorkflowResult], None] | None,
        request_id: str,
    ) -> None:
        """ワーカースレッド側で呼ばれる完了コールバック（内部専用）。

        ここでは結果の取得のみを行い、実際の通知（EventDispatcher.dispatch /
        callback 呼び出し）は ``_deliver_result()`` に委譲してメインスレッドへ
        引き渡す。実行中に例外が発生した場合も、``FAILED`` の結果を生成して
        通知し、呼び出し側が結果を待ち続けない（通知を喪失しない）ようにする。
        """
        if future.cancelled():
            # shutdown() が待機時間内に終わらなかった未実行タスクを取り消した場合
            self._deliver_result(
                WorkflowResult(
                    request_id=request_id,
                    status=ExecutionStatus.REJECTED,
                    error_message=_SHUTDOWN_REJECT_MESSAGE,
                ),
                callback,
            )
            return

        try:
            result = future.result()
        except Exception as e:
            logger.exception("TextWorkflow の非同期実行中に例外が発生しました")
            result = WorkflowResult(
                request_id=request_id,
                status=ExecutionStatus.FAILED,
                error_message=str(e) or type(e).__name__,
            )

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
                try:
                    callback(result)
                except Exception:
                    logger.exception(
                        "TextWorkflow の完了コールバックで例外が発生しました"
                    )

        if self._ui_thread_marshal is None:
            _notify()
            return

        try:
            self._ui_thread_marshal(_notify)
        except Exception:
            # 例: ウィンドウ破棄後に Tk のイベントキューへ投入できない場合
            logger.exception(
                "TextWorkflow の結果通知をUIスレッドへ引き渡せませんでした"
            )

    def shutdown(self, timeout: float = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS) -> None:
        """サービスを停止する（冪等）。

        停止後の ``execute_async()`` は ``REJECTED`` を返す。実行中・待機中の
        タスクは最大 ``timeout`` 秒だけ完了を待ち、終わらなかった未実行タスクは
        取り消して ``REJECTED`` で通知する。実行中のタスクは強制中断できないため
        放置され、完了後にワーカースレッドが終了する。

        Args:
            timeout: 完了を待つ最大秒数（UIスレッドからの呼び出しを長時間止めない）。
        """
        with self._lock:
            if self._is_shutdown:
                return
            self._is_shutdown = True
            pending = set(self._inflight)

        if pending:
            _, not_done = wait(pending, timeout=timeout)
            if not_done:
                logger.warning(
                    "TextWorkflow の実行中タスク %d 件が %s 秒以内に完了しませんでした。"
                    "未実行分は取り消します。",
                    len(not_done),
                    timeout,
                )

        # 未実行のタスクを取り消す。実行中のタスクは完了までワーカーに任せる
        self._executor.shutdown(wait=False, cancel_futures=True)
