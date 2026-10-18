"""tests/test_macos_hotkey.py

macOS (Carbon API) グローバルホットキーリスナーおよびパーサーの単体テスト。
"""

from __future__ import annotations

import ctypes
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.hotkey.global_hotkey_listener import (
    DARWIN_CMD,
    DARWIN_CTRL,
    DARWIN_OPT,
    DARWIN_SHIFT,
    HotkeyRegistration,
    format_hotkey,
    parse_hotkey_string,
)
from src.core.hotkey.hotkey_registration_manager import HotkeyRegistrationManager
from src.core.platform.macos.hotkey import (
    CWHT_SIGNATURE,
    EventHotKeyID,
    MacOSHotkeyListener,
)
from src.core.platform.protocols import HotkeyListener


def test_macos_hotkey_listener_implements_protocol() -> None:
    mock_root = MagicMock()
    mock_cb = MagicMock()
    listener = MacOSHotkeyListener(mock_root, mock_cb)
    assert isinstance(listener, HotkeyListener)


def test_parse_hotkey_string_darwin_valid() -> None:
    mods, vk = parse_hotkey_string("Cmd+Shift+F", platform="darwin")
    assert mods == (DARWIN_CMD | DARWIN_SHIFT)
    assert vk == 3  # kVK_ANSI_F

    mods2, vk2 = parse_hotkey_string("Command+Shift+V", platform="darwin")
    assert mods2 == (DARWIN_CMD | DARWIN_SHIFT)
    assert vk2 == 9  # kVK_ANSI_V

    mods3, vk3 = parse_hotkey_string("Ctrl+Opt+1", platform="darwin")
    assert mods3 == (DARWIN_CTRL | DARWIN_OPT)
    assert vk3 == 18  # kVK_ANSI_1

    mods4, vk4 = parse_hotkey_string("Win+Option+A", platform="darwin")
    assert mods4 == (DARWIN_CMD | DARWIN_OPT)
    assert vk4 == 0  # kVK_ANSI_A


def test_parse_hotkey_string_darwin_invalid() -> None:
    with pytest.raises(ValueError, match="形式が不正"):
        parse_hotkey_string("Cmd", platform="darwin")

    with pytest.raises(ValueError, match="不明な修飾キー"):
        parse_hotkey_string("UnknownMod+F", platform="darwin")

    with pytest.raises(ValueError, match="対応していない主キー"):
        parse_hotkey_string("Cmd+Shift+F1", platform="darwin")


def test_format_hotkey_darwin() -> None:
    formatted = format_hotkey(DARWIN_CMD | DARWIN_SHIFT, 3, platform="darwin")
    assert formatted == "Cmd+Shift+F"

    formatted2 = format_hotkey(DARWIN_CTRL | DARWIN_OPT, 18, platform="darwin")
    assert formatted2 == "Ctrl+Opt+1"


def test_hotkey_registration_manager_darwin() -> None:
    mock_listener = MagicMock()
    manager = HotkeyRegistrationManager(mock_listener, platform="darwin")

    mock_listener.start.return_value = True
    assert manager.reconfigure(True, "Cmd+Shift+F") is True
    assert manager.current_enabled is True
    assert manager.current_combo == "Cmd+Shift+F"


def test_macos_hotkey_listener_start_many_duplicate_ids() -> None:
    mock_root = MagicMock()
    mock_cb = MagicMock()
    listener = MacOSHotkeyListener(mock_root, mock_cb)

    reg1 = HotkeyRegistration(1, DARWIN_CMD | DARWIN_SHIFT, 3)
    reg2 = HotkeyRegistration(1, DARWIN_CMD | DARWIN_SHIFT, 9)
    assert listener.start_many([reg1, reg2]) is False


def test_macos_hotkey_listener_start_many_empty_stops() -> None:
    mock_root = MagicMock()
    mock_cb = MagicMock()
    listener = MacOSHotkeyListener(mock_root, mock_cb)

    assert listener.start_many([]) is True


def test_macos_hotkey_listener_with_mock_carbon() -> None:
    mock_carbon = MagicMock()
    mock_carbon.GetEventDispatcherTarget.return_value = 12345
    mock_carbon.InstallEventHandler.return_value = 0
    mock_carbon.RegisterEventHotKey.return_value = 0
    mock_carbon.ReceiveNextEvent.return_value = -9875  # eventLoopTimedOutErr
    mock_carbon.UnregisterEventHotKey.return_value = 0
    mock_carbon.RemoveEventHandler.return_value = 0

    mock_root = MagicMock()
    mock_cb = MagicMock()
    listener = MacOSHotkeyListener(mock_root, mock_cb, carbon_lib=mock_carbon)

    assert listener.start(DARWIN_CMD | DARWIN_SHIFT, 3) is True
    mock_carbon.InstallEventHandler.assert_called_once()
    mock_carbon.RegisterEventHotKey.assert_called_once()

    listener.stop()
    mock_carbon.RemoveEventHandler.assert_called()


def test_macos_hotkey_listener_registration_failure_rollbacks() -> None:
    mock_carbon = MagicMock()
    mock_carbon.GetEventDispatcherTarget.return_value = 12345
    mock_carbon.InstallEventHandler.return_value = 0
    # 最初の登録は成功、2番目の登録で失敗
    mock_carbon.RegisterEventHotKey.side_effect = [0, -1]
    mock_carbon.UnregisterEventHotKey.return_value = 0
    mock_carbon.RemoveEventHandler.return_value = 0

    mock_root = MagicMock()
    mock_cb = MagicMock()
    listener = MacOSHotkeyListener(mock_root, mock_cb, carbon_lib=mock_carbon)

    reg1 = HotkeyRegistration(1, DARWIN_CMD | DARWIN_SHIFT, 3)
    reg2 = HotkeyRegistration(2, DARWIN_CMD | DARWIN_SHIFT, 9)
    assert listener.start_many([reg1, reg2]) is False
    mock_carbon.UnregisterEventHotKey.assert_called_once()
    mock_carbon.RemoveEventHandler.assert_called_once()


def test_macos_hotkey_listener_event_dispatch() -> None:
    mock_carbon = MagicMock()
    mock_carbon.GetEventParameter.side_effect = (
        lambda ev, name, ty, act, sz, out_sz, data: _set_hotkey_id(data, 42)
    )

    def _set_hotkey_id(data: Any, hid: int) -> int:
        ptr = ctypes.cast(data, ctypes.POINTER(EventHotKeyID))
        ptr.contents.signature = CWHT_SIGNATURE
        ptr.contents.id = hid
        return 0

    mock_root = MagicMock()
    mock_cb = MagicMock()
    listener = MacOSHotkeyListener(mock_root, mock_cb, carbon_lib=mock_carbon)

    ret = listener._handle_carbon_event(
        ctypes.c_void_p(0), ctypes.c_void_p(0), ctypes.c_void_p(0)
    )
    assert ret == 0
    mock_root.after.assert_called_once_with(0, mock_cb, 42)


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS実環境のみで実行")
def test_macos_hotkey_listener_live_start_stop() -> None:
    mock_root = MagicMock()
    mock_cb = MagicMock()
    listener = MacOSHotkeyListener(mock_root, mock_cb)

    # Cmd+Shift+F を登録・監視開始
    ok = listener.start(DARWIN_CMD | DARWIN_SHIFT, 3)
    assert ok is True
    assert listener._running is True

    # 安全に停止
    listener.stop()
    assert listener._running is False
