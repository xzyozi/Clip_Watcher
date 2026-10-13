"""tests/test_single_instance.py

WindowsSingleInstanceController.acquire() の契約を検証する。

- True: ロックを取得した
- False: 他のインスタンスが起動中（重複起動）
- SingleInstanceError: ロック取得 API の失敗（重複起動とは区別する）
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from src.core.platform.errors import SingleInstanceError
from src.core.platform.windows.single_instance import (
    WindowsSingleInstanceController,
)

_ERROR_ALREADY_EXISTS = 183


@pytest.fixture
def kernel32(monkeypatch: pytest.MonkeyPatch) -> Iterator[MagicMock]:
    """Windows API を差し替え、kernel32 のモックを提供する。"""
    monkeypatch.setattr(sys, "platform", "win32")
    mock_kernel32 = MagicMock()
    with (
        patch("ctypes.WinDLL", create=True, return_value=mock_kernel32),
        patch("ctypes.get_last_error", create=True, return_value=0) as last_error,
    ):
        mock_kernel32.last_error = last_error
        yield mock_kernel32


def test_acquire_returns_true_when_lock_is_obtained(kernel32: MagicMock) -> None:
    kernel32.CreateMutexW.return_value = 1234

    assert WindowsSingleInstanceController().acquire() is True


def test_acquire_returns_false_when_another_instance_is_running(
    kernel32: MagicMock,
) -> None:
    kernel32.CreateMutexW.return_value = 1234
    kernel32.last_error.return_value = _ERROR_ALREADY_EXISTS

    assert WindowsSingleInstanceController().acquire() is False
    kernel32.CloseHandle.assert_called_once()


def test_acquire_raises_single_instance_error_when_api_fails(
    kernel32: MagicMock,
) -> None:
    """CreateMutexW の失敗は重複起動ではなく SingleInstanceError にする。"""
    kernel32.CreateMutexW.return_value = None
    kernel32.last_error.return_value = 5

    with pytest.raises(SingleInstanceError):
        WindowsSingleInstanceController().acquire()


def test_acquire_wraps_unexpected_exception_in_single_instance_error(
    kernel32: MagicMock,
) -> None:
    kernel32.CreateMutexW.side_effect = OSError("boom")

    with pytest.raises(SingleInstanceError):
        WindowsSingleInstanceController().acquire()


def test_release_closes_handle_only_once(kernel32: MagicMock) -> None:
    kernel32.CreateMutexW.return_value = 1234
    controller = WindowsSingleInstanceController()
    assert controller.acquire() is True

    controller.release()
    controller.release()

    assert kernel32.CloseHandle.call_count == 1


def test_release_without_acquire_does_nothing(kernel32: MagicMock) -> None:
    WindowsSingleInstanceController().release()

    kernel32.CloseHandle.assert_not_called()
