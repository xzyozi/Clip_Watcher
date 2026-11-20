"""GlobalHotkeyListener の登録・メッセージループと、macOS 向けのキー変換のテスト。

Windows API（ctypes.windll）は偽物に差し替えるため、全 OS で実行できる。
"""

from __future__ import annotations

import ctypes
import sys
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.hotkey import global_hotkey_listener as module
from src.core.hotkey.global_hotkey_listener import (
    DARWIN_CMD,
    DARWIN_CTRL,
    DARWIN_OPT,
    DARWIN_SHIFT,
    GLOBAL_HOTKEY_ID,
    MOD_ALT,
    MOD_CONTROL,
    MOD_NOREPEAT,
    MOD_SHIFT,
    MOD_WIN,
    WM_HOTKEY,
    WM_QUIT,
    GlobalHotkeyListener,
    HotkeyRegistration,
    format_hotkey,
    parse_hotkey_string,
)

# --- キー文字列の変換 ---


def test_parse_darwin_combo_uses_carbon_codes() -> None:
    modifiers, key = parse_hotkey_string("Cmd+Shift+A", platform="darwin")
    assert modifiers == DARWIN_CMD | DARWIN_SHIFT
    assert key == 0

    modifiers, key = parse_hotkey_string("Ctrl+Opt+9", platform="darwin")
    assert modifiers == DARWIN_CTRL | DARWIN_OPT
    assert key == 25


@pytest.mark.parametrize("combo", ["Cmd+Shift+F13", "Hyper+A", "A"])
def test_parse_darwin_rejects_invalid_combos(combo: str) -> None:
    with pytest.raises(ValueError):
        parse_hotkey_string(combo, platform="darwin")


def test_parse_windows_rejects_empty_key_part() -> None:
    with pytest.raises(ValueError):
        parse_hotkey_string("Ctrl++", platform="win32")


def test_parse_uses_current_platform_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    assert parse_hotkey_string("Cmd+A") == (DARWIN_CMD, 0)
    monkeypatch.setattr(sys, "platform", "win32")
    assert parse_hotkey_string("Win+A") == (MOD_WIN, ord("A"))


def test_format_darwin_combo_orders_modifiers() -> None:
    combo = format_hotkey(
        DARWIN_CMD | DARWIN_CTRL | DARWIN_OPT | DARWIN_SHIFT, 0, platform="darwin"
    )
    assert combo == "Cmd+Ctrl+Opt+Shift+A"


def test_format_darwin_falls_back_to_character_for_unknown_code() -> None:
    assert format_hotkey(DARWIN_CMD, ord("Z") + 1000, platform="darwin").startswith(
        "Cmd+"
    )


def test_format_windows_combo_includes_all_modifiers() -> None:
    combo = format_hotkey(
        MOD_CONTROL | MOD_ALT | MOD_SHIFT | MOD_WIN, ord("K"), platform="win32"
    )
    assert combo == "Ctrl+Alt+Shift+Win+K"


def test_format_uses_current_platform_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert format_hotkey(MOD_CONTROL, ord("A")) == "Ctrl+A"


# --- GlobalHotkeyListener ---


class FakeWin32:
    """ctypes.windll の最小の偽物。メッセージループの戻り値を順に返す。"""

    def __init__(
        self, register_results: list[int], loop_results: list[tuple[int, int, int]]
    ) -> None:
        self.register_results = list(register_results)
        self.loop_results = list(loop_results)
        self.registered: list[tuple[int, int, int]] = []
        self.unregistered: list[int] = []
        self.posted: list[tuple[int, int]] = []
        self.user32 = SimpleNamespace(
            RegisterHotKey=self._register,
            UnregisterHotKey=lambda _hwnd, hotkey_id: self.unregistered.append(
                hotkey_id
            ),
            GetMessageW=self._get_message,
            PostThreadMessageW=lambda tid, msg, _w, _p: self.posted.append((tid, msg)),
        )
        self.kernel32 = SimpleNamespace(
            GetCurrentThreadId=lambda: 4242, GetLastError=lambda: 5
        )

    def _register(self, _hwnd: Any, hotkey_id: int, modifiers: int, vk: int) -> int:
        self.registered.append((hotkey_id, modifiers, vk))
        return self.register_results.pop(0)

    def _get_message(self, ref: Any, *_args: Any) -> int:
        ret, message_id, wparam = self.loop_results.pop(0)
        msg = ref._obj
        msg.message = message_id
        msg.wParam = wparam
        return ret


@pytest.fixture
def win32(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeWin32]:
    fake = FakeWin32(register_results=[1, 1, 1], loop_results=[])
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(user32=fake.user32, kernel32=fake.kernel32),
        raising=False,
    )
    yield fake


def _listener() -> tuple[GlobalHotkeyListener, MagicMock, MagicMock]:
    root = MagicMock()
    callback = MagicMock()
    return GlobalHotkeyListener(root, callback), root, callback


def test_start_many_rejects_duplicate_ids() -> None:
    listener, _, _ = _listener()
    entries = [HotkeyRegistration(1, MOD_CONTROL, 65), HotkeyRegistration(1, 0, 66)]
    assert listener.start_many(entries) is False


def test_start_many_with_no_entries_stops_listener() -> None:
    listener, _, _ = _listener()
    assert listener.start_many([]) is True
    assert listener._thread is None


def test_start_many_is_skipped_on_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    listener, _, _ = _listener()
    assert listener.start(MOD_CONTROL, 65) is False


def test_hotkey_message_is_forwarded_to_tk_main_thread(win32: FakeWin32) -> None:
    win32.register_results = [1, 1]
    win32.loop_results = [(1, WM_HOTKEY, 7), (1, 0x0001, 0), (0, 0, 0)]
    listener, root, callback = _listener()

    ok = listener.start_many(
        [
            HotkeyRegistration(GLOBAL_HOTKEY_ID, MOD_CONTROL | MOD_SHIFT, ord("F")),
            HotkeyRegistration(2, MOD_ALT, ord("G")),
        ]
    )
    assert listener._thread is not None
    listener._thread.join(timeout=3)

    assert ok is True
    assert win32.registered == [
        (GLOBAL_HOTKEY_ID, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, ord("F")),
        (2, MOD_ALT | MOD_NOREPEAT, ord("G")),
    ]
    root.after.assert_called_once_with(0, callback, 7)
    assert sorted(win32.unregistered) == [1, 2]  # ループ終了時に全て解除される


def test_registration_failure_rolls_back_previous_registrations(
    win32: FakeWin32,
) -> None:
    win32.register_results = [1, 0]  # 2件目で競合
    listener, root, _ = _listener()
    ok = listener.start_many(
        [HotkeyRegistration(1, MOD_CONTROL, 65), HotkeyRegistration(2, MOD_CONTROL, 66)]
    )
    if listener._thread is not None:
        listener._thread.join(timeout=3)
    assert ok is False
    # 失敗時の巻き戻しと終了処理の双方で解除されるため、重複は許容して集合で確認する
    assert set(win32.unregistered) == {1}
    root.after.assert_not_called()


def test_message_loop_stops_on_getmessage_error(win32: FakeWin32) -> None:
    win32.register_results = [1]
    win32.loop_results = [(-1, 0, 0)]
    listener, root, _ = _listener()
    assert listener.start(MOD_CONTROL, 65) is True
    assert listener._thread is not None
    listener._thread.join(timeout=3)
    assert win32.unregistered == [GLOBAL_HOTKEY_ID]
    root.after.assert_not_called()


def test_stop_posts_quit_message_and_clears_thread_state(win32: FakeWin32) -> None:
    listener, _, _ = _listener()
    listener._thread_id = 99
    listener._running = True
    listener.stop()
    assert win32.posted == [(99, WM_QUIT)]
    assert (listener._thread, listener._thread_id, listener._running) == (
        None,
        None,
        False,
    )


def test_stop_without_thread_is_a_noop() -> None:
    listener, _, _ = _listener()
    listener.stop()
    assert listener._thread is None


def test_module_exports_expected_constants() -> None:
    assert module.WM_HOTKEY == WM_HOTKEY
    assert module.GLOBAL_HOTKEY_ID == GLOBAL_HOTKEY_ID
