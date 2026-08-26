from __future__ import annotations

import ctypes
import logging
import sys
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk

logger = logging.getLogger(__name__)

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
HOTKEY_ID = 1

_MODIFIER_MAP = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "super": MOD_WIN,
}


def parse_hotkey_string(combo: str) -> tuple[int, int]:
    """
    "Ctrl+Shift+F" のような文字列を (modifiers, vk_code) に変換する。
    不正な形式の場合は ValueError を投げる。
    """
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if len(parts) < 2:
        raise ValueError(f"ホットキー文字列の形式が不正です: {combo!r}")

    modifiers = 0
    key_part = parts[-1]
    for mod in parts[:-1]:
        if mod not in _MODIFIER_MAP:
            raise ValueError(f"不明な修飾キーです: {mod!r}")
        modifiers |= _MODIFIER_MAP[mod]

    if len(key_part) != 1 or not key_part.isalnum():
        raise ValueError(f"対応していない主キーです: {key_part!r}")

    vk_code = ord(key_part.upper())
    return modifiers, vk_code


def format_hotkey(modifiers: int, vk_code: int) -> str:
    """(modifiers, vk_code) から "Ctrl+Shift+F" 形式の文字列を生成する。"""
    parts = []
    if modifiers & MOD_CONTROL:
        parts.append("Ctrl")
    if modifiers & MOD_ALT:
        parts.append("Alt")
    if modifiers & MOD_SHIFT:
        parts.append("Shift")
    if modifiers & MOD_WIN:
        parts.append("Win")
    parts.append(chr(vk_code))
    return "+".join(parts)


class GlobalHotkeyListener:
    """RegisterHotKey を用いてグローバルホットキーを監視するクラス。

    専用スレッド + tk_root.after() でメインスレッドへ安全に橋渡しする。
    """

    def __init__(self, tk_root: tk.Tk, on_triggered: Callable[[], None]) -> None:
        self.tk_root = tk_root
        self.on_triggered = on_triggered
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._running = False

    def start(self, modifiers: int, vk_code: int) -> bool:
        if self._running:
            self.stop()

        if sys.platform != "win32":
            logger.warning("Windows 以外の環境のため、グローバルホットキー登録をスキップします。")
            return False

        import ctypes.wintypes

        result_holder: dict[str, bool] = {}
        ready_event = threading.Event()

        def _run() -> None:
            user32 = ctypes.windll.user32
            self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

            ok = user32.RegisterHotKey(None, HOTKEY_ID, modifiers | MOD_NOREPEAT, vk_code)
            result_holder["ok"] = bool(ok)
            ready_event.set()

            if not ok:
                logger.warning("グローバルホットキーの登録に失敗しました（キー競合の可能性）。")
                return

            msg = ctypes.wintypes.MSG()
            self._running = True
            try:
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                        self.tk_root.after(0, self.on_triggered)
            finally:
                user32.UnregisterHotKey(None, HOTKEY_ID)
                self._running = False

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        ready_event.wait(timeout=1.0)
        return result_holder.get("ok", False)

    def stop(self) -> None:
        if sys.platform == "win32" and self._thread_id is not None:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._thread_id = None
        self._running = False
