"""tests/unit/test_text_workflow_service_robustness.py

TextWorkflowService の非同期実行で、例外発生時にも完了通知が失われないこと (#132)、
およびシャットダウン時の挙動 (#135) を検証する。
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

from src.core.text_workflow.models import (
    ExecutionStatus,
    SourceKind,
    WorkflowRequest,
    WorkflowResult,
)
from src.services.text_workflow_service import (
    TEXT_WORKFLOW_RESULT_EVENT,
    TextWorkflowService,
)


def _request(request_id: str = "req-1") -> WorkflowRequest:
    return WorkflowRequest(
        request_id=request_id,
        source_kind=SourceKind.EXPLICIT_TEXT,
        input_text="text",
        save_history=False,
    )


def _service(
    workflow: Any, dispatcher: Any | None = None, **kwargs: Any
) -> TextWorkflowService:
    return TextWorkflowService(
        workflow=workflow,
        event_dispatcher=dispatcher,
        ui_thread_marshal=lambda fn: fn(),
        **kwargs,
    )


def _failing_workflow(error: Exception) -> MagicMock:
    workflow = MagicMock()
    workflow.execute.side_effect = error
    return workflow


def _await(callback_done: threading.Event) -> None:
    assert callback_done.wait(timeout=5.0), "完了通知が届かなかった"


class TestExceptionNotification:
    def test_failed_result_is_delivered_when_workflow_raises(self) -> None:
        dispatcher = MagicMock()
        received: list[WorkflowResult] = []
        done = threading.Event()

        def callback(result: WorkflowResult) -> None:
            received.append(result)
            done.set()

        service = _service(_failing_workflow(RuntimeError("boom")), dispatcher)
        try:
            service.execute_async(_request("req-x"), callback=callback)
            _await(done)
        finally:
            service.shutdown()

        assert len(received) == 1
        result = received[0]
        assert result.request_id == "req-x"
        assert result.status is ExecutionStatus.FAILED
        assert result.error_message == "boom"
        dispatcher.dispatch.assert_called_once_with(TEXT_WORKFLOW_RESULT_EVENT, result)

    def test_error_message_falls_back_to_exception_type_name(self) -> None:
        received: list[WorkflowResult] = []
        done = threading.Event()

        def callback(result: WorkflowResult) -> None:
            received.append(result)
            done.set()

        service = _service(_failing_workflow(ValueError()))
        try:
            service.execute_async(_request(), callback=callback)
            _await(done)
        finally:
            service.shutdown()

        assert received[0].error_message == "ValueError"

    def test_exception_in_callback_does_not_propagate(self) -> None:
        dispatched = threading.Event()
        dispatcher = MagicMock()
        dispatcher.dispatch.side_effect = lambda *a, **k: dispatched.set()

        def bad_callback(result: WorkflowResult) -> None:
            raise RuntimeError("callback failure")

        service = _service(_failing_workflow(RuntimeError("boom")), dispatcher)
        try:
            service.execute_async(_request(), callback=bad_callback)
            _await(dispatched)
        finally:
            service.shutdown()

    def test_marshal_failure_does_not_raise_in_worker(self) -> None:
        marshal_called = threading.Event()

        def broken_marshal(fn: Callable[[], None]) -> None:
            marshal_called.set()
            raise RuntimeError("main thread is gone")

        service = TextWorkflowService(
            workflow=_failing_workflow(RuntimeError("boom")),
            ui_thread_marshal=broken_marshal,
        )
        try:
            service.execute_async(_request())
            _await(marshal_called)
        finally:
            service.shutdown()


def _ok_result(request: WorkflowRequest) -> WorkflowResult:
    return WorkflowResult(
        request_id=request.request_id,
        status=ExecutionStatus.COMPLETED,
        output_text=request.input_text,
    )


class TestShutdown:
    def test_execute_after_shutdown_is_rejected_without_running(self) -> None:
        workflow = MagicMock()
        service = _service(workflow)
        service.shutdown()
        received: list[WorkflowResult] = []

        future = service.execute_async(_request("late"), callback=received.append)

        workflow.execute.assert_not_called()
        assert future.done()
        result = future.result(timeout=1.0)
        assert result.status is ExecutionStatus.REJECTED
        assert result.request_id == "late"
        # 完了通知も同じ経路で届く
        assert received == [result]

    def test_shutdown_waits_for_running_task_to_finish(self) -> None:
        finished = threading.Event()

        def slow_execute(request: WorkflowRequest) -> WorkflowResult:
            threading.Event().wait(0.2)
            finished.set()
            return _ok_result(request)

        workflow = MagicMock()
        workflow.execute.side_effect = slow_execute
        service = _service(workflow)

        future = service.execute_async(_request())
        service.shutdown(timeout=5.0)

        assert finished.is_set()
        assert future.result(timeout=1.0).status is ExecutionStatus.COMPLETED

    def test_shutdown_returns_after_timeout_and_rejects_queued_tasks(self) -> None:
        release = threading.Event()
        started = threading.Event()

        def blocking_execute(request: WorkflowRequest) -> WorkflowResult:
            started.set()
            release.wait(timeout=10.0)
            return _ok_result(request)

        workflow = MagicMock()
        workflow.execute.side_effect = blocking_execute
        service = _service(workflow, max_workers=1)
        queued_results: list[WorkflowResult] = []

        running = service.execute_async(_request("running"))
        assert started.wait(timeout=5.0)
        queued = service.execute_async(
            _request("queued"), callback=queued_results.append
        )
        try:
            service.shutdown(timeout=0.1)  # 実行中タスクは終わらないが戻ってくる

            assert queued.cancelled()
            assert [r.request_id for r in queued_results] == ["queued"]
            assert queued_results[0].status is ExecutionStatus.REJECTED
            assert not running.done()
        finally:
            release.set()

        assert running.result(timeout=5.0).status is ExecutionStatus.COMPLETED

    def test_shutdown_is_idempotent(self) -> None:
        service = _service(MagicMock())

        service.shutdown()
        service.shutdown()
