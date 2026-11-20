"""OS 別アダプターとメインハンドラの補足テスト。

Windows API・fcntl・Objective-C ランタイムは偽物へ差し替えるため、全 OS で実行できる。
これにより Windows/Ubuntu/macOS のどの CI でも同じ経路を検証できる。
"""

from __future__ import annotations

import ctypes
import ctypes.util
import ctypes.wintypes  # noqa: F401  (Windows 用アダプターが参照する)
import errno
import sys
import tkinter as tk
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.platform.errors import SingleInstanceError
from src.core.platform.macos import process_inspector as mac_inspector
from src.core.platform.posix.single_instance import PosixSingleInstanceController
from src.core.platform.windows.paste_sender import WindowsPasteSender
from src.core.platform.windows.process_inspector import WindowsProcessInspector
from src.event_handlers import main_handlers

# --- Windows: 貼り付け送信 ---


@pytest.fixture
def fake_windll(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    user32 = SimpleNamespace(
        GetAsyncKeyState=MagicMock(return_value=0),
        keybd_event=MagicMock(),
        GetForegroundWindow=MagicMock(return_value=1),
        GetWindowThreadProcessId=MagicMock(),
    )
    kernel32 = SimpleNamespace(
        OpenProcess=MagicMock(return_value=5), CloseHandle=MagicMock()
    )
    psapi = SimpleNamespace(GetModuleBaseNameA=MagicMock())
    windll = SimpleNamespace(user32=user32, kernel32=kernel32, psapi=psapi)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)
    return windll


def test_windows_modifiers_released_when_no_key_is_down(
    fake_windll: SimpleNamespace,
) -> None:
    assert WindowsPasteSender().are_modifiers_released() is True


def test_windows_modifiers_not_released_when_any_key_is_down(
    fake_windll: SimpleNamespace,
) -> None:
    fake_windll.user32.GetAsyncKeyState.side_effect = lambda vk: (
        0x8000 if vk == 0x11 else 0
    )
    assert WindowsPasteSender().are_modifiers_released() is False


def test_windows_modifier_query_failure_is_treated_as_not_released(
    fake_windll: SimpleNamespace,
) -> None:
    fake_windll.user32.GetAsyncKeyState.side_effect = OSError("api error")
    assert WindowsPasteSender().are_modifiers_released() is False


def test_windows_paste_sends_ctrl_v_sequence(fake_windll: SimpleNamespace) -> None:
    assert WindowsPasteSender().paste_active_window() is True
    sent = [c.args for c in fake_windll.user32.keybd_event.call_args_list]
    assert sent == [
        (0x11, 0, 0, 0),
        (0x56, 0, 0, 0),
        (0x56, 0, 0x0002, 0),
        (0x11, 0, 0x0002, 0),
    ]


def test_windows_paste_reports_api_failure(fake_windll: SimpleNamespace) -> None:
    fake_windll.user32.keybd_event.side_effect = OSError("blocked")
    assert WindowsPasteSender().paste_active_window() is False


def test_windows_paste_sender_is_inert_on_other_platforms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    sender = WindowsPasteSender()
    assert sender.are_modifiers_released() is False
    assert sender.paste_active_window() is False


# --- Windows: プロセス名の取得 ---


def _fill_pid(pid_value: int) -> Any:
    def get_pid(_hwnd: int, pid_ref: Any) -> None:
        pid_ref._obj.value = pid_value

    return get_pid


def _fill_name(name: bytes) -> Any:
    def get_name(_handle: int, _module: Any, buffer: Any, _size: int) -> None:
        buffer.value = name

    return get_name


def test_windows_inspector_returns_foreground_process_name(
    fake_windll: SimpleNamespace,
) -> None:
    fake_windll.user32.GetWindowThreadProcessId.side_effect = _fill_pid(321)
    fake_windll.psapi.GetModuleBaseNameA.side_effect = _fill_name(b"notepad.exe")
    assert WindowsProcessInspector().get_active_process_name() == "notepad.exe"
    fake_windll.kernel32.OpenProcess.assert_called_once_with(0x0410, False, 321)
    fake_windll.kernel32.CloseHandle.assert_called_once_with(5)


def test_windows_inspector_returns_none_without_foreground_window(
    fake_windll: SimpleNamespace,
) -> None:
    fake_windll.user32.GetForegroundWindow.return_value = 0
    assert WindowsProcessInspector().get_active_process_name() is None


def test_windows_inspector_returns_none_when_process_cannot_be_opened(
    fake_windll: SimpleNamespace,
) -> None:
    fake_windll.kernel32.OpenProcess.return_value = 0
    assert WindowsProcessInspector().get_active_process_name() is None


def test_windows_inspector_swallows_api_errors(fake_windll: SimpleNamespace) -> None:
    fake_windll.user32.GetForegroundWindow.side_effect = OSError("boom")
    assert WindowsProcessInspector().get_active_process_name() is None


def test_windows_inspector_is_inert_on_other_platforms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert WindowsProcessInspector().get_active_process_name() is None


# --- POSIX: 多重起動の排他 ---


@pytest.fixture
def fake_fcntl(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module = ModuleType("fcntl")
    module.LOCK_EX = 2  # type: ignore[attr-defined]
    module.LOCK_NB = 4  # type: ignore[attr-defined]
    module.LOCK_UN = 8  # type: ignore[attr-defined]
    module.flock = MagicMock()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fcntl", module)
    return module


def test_posix_acquire_writes_pid_and_release_unlocks(
    tmp_path: Path, fake_fcntl: ModuleType
) -> None:
    lock = tmp_path / "nested" / "app.lock"
    controller = PosixSingleInstanceController(lock)
    assert controller.acquire() is True
    assert lock.read_text(encoding="utf-8").strip().isdigit()
    controller.release()
    assert fake_fcntl.flock.call_args.args[1] == fake_fcntl.LOCK_UN  # type: ignore[attr-defined]
    controller.release()  # 二重解放しても何も起きない


def test_posix_acquire_reports_running_instance(
    tmp_path: Path, fake_fcntl: ModuleType
) -> None:
    fake_fcntl.flock.side_effect = BlockingIOError()  # type: ignore[attr-defined]
    assert PosixSingleInstanceController(tmp_path / "a.lock").acquire() is False


@pytest.mark.parametrize("code", [errno.EACCES, errno.EAGAIN])
def test_posix_acquire_treats_lock_errnos_as_running_instance(
    tmp_path: Path, fake_fcntl: ModuleType, code: int
) -> None:
    fake_fcntl.flock.side_effect = OSError(code, "locked")  # type: ignore[attr-defined]
    assert PosixSingleInstanceController(tmp_path / "a.lock").acquire() is False


def test_posix_acquire_raises_for_unexpected_flock_failure(
    tmp_path: Path, fake_fcntl: ModuleType
) -> None:
    fake_fcntl.flock.side_effect = OSError(errno.EIO, "io")  # type: ignore[attr-defined]
    with pytest.raises(SingleInstanceError):
        PosixSingleInstanceController(tmp_path / "a.lock").acquire()


def test_posix_acquire_raises_when_fcntl_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "fcntl", None)
    with pytest.raises(SingleInstanceError, match="fcntl"):
        PosixSingleInstanceController(tmp_path / "a.lock").acquire()


def test_posix_acquire_raises_when_lock_file_cannot_be_opened(
    tmp_path: Path, fake_fcntl: ModuleType
) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(SingleInstanceError, match="オープン"):
        PosixSingleInstanceController(blocker / "child.lock").acquire()


def test_posix_release_tolerates_unlock_errors(
    tmp_path: Path, fake_fcntl: ModuleType
) -> None:
    controller = PosixSingleInstanceController(tmp_path / "a.lock")
    controller.acquire()
    fake_fcntl.flock.side_effect = OSError("cannot unlock")  # type: ignore[attr-defined]
    controller.release()
    assert controller._file is None


def test_posix_default_lock_path_is_under_home() -> None:
    controller = PosixSingleInstanceController()
    assert controller.lock_file_path.name == "clip_watcher.lock"


# --- macOS: プロセス名の取得 ---


def _patch_objc(
    monkeypatch: pytest.MonkeyPatch, send_results: list[Any], name: bytes | None
) -> None:
    """objc_msgSend 相当の偽物を用意し、AppKit 経路を差し替える。"""
    monkeypatch.setattr(ctypes.util, "find_library", lambda name_: f"/lib/{name_}")
    monkeypatch.setattr(ctypes, "cdll", MagicMock())
    results = iter(send_results)
    send = MagicMock(side_effect=lambda *a: next(results))
    send_str = MagicMock(return_value=name)
    casts = iter([send, send_str])
    monkeypatch.setattr(ctypes, "cast", lambda *a: next(casts))


def test_appkit_lookup_returns_frontmost_application_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_objc(monkeypatch, [11, 22, 33], b"Safari")
    assert mac_inspector._get_active_process_via_appkit() == "Safari"


@pytest.mark.parametrize(
    "send_results",
    [[11, 0], [11, 22, 0]],
    ids=["no-frontmost-app", "no-localized-name"],
)
def test_appkit_lookup_stops_at_first_missing_object(
    monkeypatch: pytest.MonkeyPatch, send_results: list[int]
) -> None:
    _patch_objc(monkeypatch, send_results, b"x")
    assert mac_inspector._get_active_process_via_appkit() is None


def test_appkit_lookup_returns_none_for_empty_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_objc(monkeypatch, [11, 22, 33], b"")
    assert mac_inspector._get_active_process_via_appkit() is None


def test_appkit_lookup_returns_none_without_workspace_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ctypes.util, "find_library", lambda name_: f"/lib/{name_}")
    objc = MagicMock()
    objc.objc_getClass.return_value = 0
    monkeypatch.setattr(ctypes, "cdll", MagicMock(LoadLibrary=lambda path: objc))
    assert mac_inspector._get_active_process_via_appkit() is None


def test_appkit_lookup_returns_none_when_workspace_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_objc(monkeypatch, [0], b"x")
    assert mac_inspector._get_active_process_via_appkit() is None


# --- メインハンドラ ---


def test_about_and_how_to_use_show_information_dialogs() -> None:
    with patch.object(main_handlers.messagebox, "showinfo") as show:
        main_handlers.handle_about()
        main_handlers.handle_how_to_use()
    assert show.call_count == 2
    assert "ClipWatcher" in show.call_args_list[0].args[1]


def test_copy_fixed_phrase_sets_clipboard() -> None:
    gui = MagicMock()
    main_handlers.handle_copy_fixed_phrase(gui, "hello")
    gui.master.clipboard_clear.assert_called_once()
    gui.master.clipboard_append.assert_called_once_with("hello")


def test_copy_fixed_phrase_reports_clipboard_errors() -> None:
    gui = MagicMock()
    gui.master.clipboard_clear.side_effect = RuntimeError("no clipboard")
    with patch.object(main_handlers, "log_and_show_error") as report:
        main_handlers.handle_copy_fixed_phrase(gui, "hello")
    report.assert_called_once()


def test_show_schedule_helper_selects_calendar_tab() -> None:
    app = MagicMock()
    main_handlers.handle_show_schedule_helper_tool(app)
    app.gui.notebook.select.assert_called_once_with(2)


def test_show_schedule_helper_tolerates_missing_tab() -> None:
    app = MagicMock()
    app.gui.notebook.select.side_effect = tk.TclError("no such tab")
    with patch.object(main_handlers, "log_and_show_error") as report:
        main_handlers.handle_show_schedule_helper_tool(app)
    report.assert_not_called()


def test_show_schedule_helper_reports_unexpected_errors() -> None:
    app = MagicMock()
    app.gui.notebook.select.side_effect = RuntimeError("boom")
    with patch.object(main_handlers, "log_and_show_error") as report:
        main_handlers.handle_show_schedule_helper_tool(app)
    report.assert_called_once()
