"""MacOSHotkeyListener を偽の Carbon ライブラリで動かすテスト（全 OS で実行可能）。"""

from __future__ import annotations

import ctypes
import sys
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.hotkey.global_hotkey_listener import (
    GLOBAL_HOTKEY_ID,
    HotkeyRegistration,
)
from src.core.platform.macos import hotkey as hotkey_module
from src.core.platform.macos.hotkey import (
    CWHT_SIGNATURE,
    MacOSHotkeyListener,
    _load_carbon,
)


def _carbon(
    *, install_status: int = 0, register_statuses: list[int] | None = None
) -> MagicMock:
    carbon = MagicMock()
    carbon.InstallEventHandler.return_value = install_status
    statuses = list(register_statuses if register_statuses is not None else [0, 0, 0])
    carbon.RegisterEventHotKey.side_effect = lambda *args: statuses.pop(0)
    # ReceiveNextEvent は常に「イベントなし」（タイムアウト）を返す
    carbon.ReceiveNextEvent.return_value = -9875
    return carbon


def _listener(carbon: MagicMock | None) -> tuple[MacOSHotkeyListener, MagicMock]:
    root = MagicMock()
    listener = MacOSHotkeyListener(root, MagicMock(), carbon_lib=carbon)
    return listener, root


def test_start_registers_hotkeys_and_stop_releases_them() -> None:
    carbon = _carbon()
    listener, _ = _listener(carbon)

    ok = listener.start_many(
        [HotkeyRegistration(1, 0x0100, 3), HotkeyRegistration(2, 0x0200, 9)]
    )
    assert ok is True
    assert carbon.RegisterEventHotKey.call_count == 2
    first_call = carbon.RegisterEventHotKey.call_args_list[0].args
    assert first_call[0] == 3  # 仮想キーコード
    assert first_call[1] == 0x0100  # 修飾キー
    assert first_call[2].signature == CWHT_SIGNATURE
    assert first_call[2].id == 1

    listener.stop()
    assert carbon.UnregisterEventHotKey.call_count == 2
    carbon.RemoveEventHandler.assert_called_once()
    assert listener._thread is None


def test_single_start_uses_global_hotkey_id() -> None:
    carbon = _carbon(register_statuses=[0])
    listener, _ = _listener(carbon)
    assert listener.start(0x0100, 3) is True
    assert carbon.RegisterEventHotKey.call_args.args[2].id == GLOBAL_HOTKEY_ID
    listener.stop()


def test_event_loop_forwards_received_events_to_carbon() -> None:
    carbon = _carbon(register_statuses=[0])
    delivered: list[Any] = []

    def receive(_n: int, _types: Any, _timeout: Any, _pull: int, out_ref: Any) -> int:
        if not delivered:
            out_ref._obj.value = 1234
            delivered.append(True)
            return 0
        return -9875

    carbon.ReceiveNextEvent.side_effect = receive
    listener, _ = _listener(carbon)
    listener.start(0x0100, 3)
    for _ in range(50):
        if carbon.SendEventToEventTarget.called:
            break
        time.sleep(0.02)
    listener.stop()

    carbon.SendEventToEventTarget.assert_called_once()
    carbon.ReleaseEvent.assert_called_once()


def test_registration_failure_rolls_back_and_reports_false() -> None:
    carbon = _carbon(register_statuses=[0, -1])
    listener, _ = _listener(carbon)
    ok = listener.start_many(
        [HotkeyRegistration(1, 0x0100, 3), HotkeyRegistration(2, 0x0100, 9)]
    )
    assert ok is False
    carbon.UnregisterEventHotKey.assert_called_once()
    carbon.RemoveEventHandler.assert_called_once()
    listener.stop()


def test_handler_installation_failure_reports_false() -> None:
    carbon = _carbon(install_status=-50)
    listener, _ = _listener(carbon)
    assert listener.start(0x0100, 3) is False
    carbon.RegisterEventHotKey.assert_not_called()
    listener.stop()


def test_duplicate_ids_and_empty_registrations() -> None:
    carbon = _carbon()
    listener, _ = _listener(carbon)
    assert listener.start_many([HotkeyRegistration(1, 0, 3)] * 2) is False
    assert listener.start_many([]) is True
    carbon.InstallEventHandler.assert_not_called()


def test_start_is_skipped_on_other_platforms_without_carbon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    listener, _ = _listener(None)
    assert listener.start(0x0100, 3) is False


def test_start_fails_when_carbon_cannot_be_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(hotkey_module, "_load_carbon", lambda: None)
    listener, _ = _listener(None)
    assert listener.start(0x0100, 3) is False


# --- Carbon イベントの処理 ---


def _event_parameter(hotkey_id: int, status: int = 0) -> Any:
    def get_parameter(_event: Any, _name: int, _type: int, *args: Any) -> int:
        out = args[-1]._obj
        out.id = hotkey_id
        return status

    return get_parameter


def test_carbon_event_triggers_callback_on_tk_thread() -> None:
    carbon = MagicMock()
    carbon.GetEventParameter.side_effect = _event_parameter(7)
    listener, root = _listener(carbon)
    assert listener._handle_carbon_event(None, None, None) == 0  # type: ignore[arg-type]
    root.after.assert_called_once_with(0, listener.on_triggered, 7)


def test_carbon_event_with_parameter_error_is_ignored() -> None:
    carbon = MagicMock()
    carbon.GetEventParameter.side_effect = _event_parameter(7, status=-1)
    listener, root = _listener(carbon)
    listener._handle_carbon_event(None, None, None)  # type: ignore[arg-type]
    root.after.assert_not_called()


def test_carbon_event_survives_dispatch_failure() -> None:
    carbon = MagicMock()
    carbon.GetEventParameter.side_effect = _event_parameter(7)
    listener, root = _listener(carbon)
    root.after.side_effect = RuntimeError("tk is gone")
    assert listener._handle_carbon_event(None, None, None) == 0  # type: ignore[arg-type]


def test_carbon_event_without_library_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hotkey_module, "_load_carbon", lambda: None)
    listener, root = _listener(None)
    assert listener._handle_carbon_event(None, None, None) == 0  # type: ignore[arg-type]
    root.after.assert_not_called()


def test_stop_without_thread_is_safe() -> None:
    listener, _ = _listener(_carbon())
    listener.stop()
    assert listener._thread is None


# --- Carbon のロード ---


def test_load_carbon_returns_none_off_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert _load_carbon() is None


def test_load_carbon_returns_none_when_framework_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    cdll = MagicMock()
    cdll.LoadLibrary.side_effect = OSError("not found")
    monkeypatch.setattr(ctypes, "cdll", cdll)
    assert _load_carbon() is None


def test_load_carbon_configures_function_prototypes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    library = MagicMock()
    cdll = MagicMock()
    cdll.LoadLibrary.return_value = library
    monkeypatch.setattr(ctypes, "cdll", cdll)

    loaded = _load_carbon()

    assert loaded is library
    assert library.RegisterEventHotKey.restype is hotkey_module.OSStatus
    assert len(library.RegisterEventHotKey.argtypes) == 6
    assert library.ReleaseEvent.restype is None
