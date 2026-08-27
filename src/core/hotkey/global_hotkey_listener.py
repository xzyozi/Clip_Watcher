from __future__ import annotations

import ctypes
import logging
import sys
import threading
import tkinter as tk
from collections.abc import Callable, Iterable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
GLOBAL_HOTKEY_ID = 1

_MODIFIER_MAP = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "super": MOD_WIN,
}


@dataclass(frozen=True)
class HotkeyRegistration:
    """Windows に登録するホットキーの不変な定義。"""

    hotkey_id: int
    modifiers: int
    vk_code: int


def parse_hotkey_string(combo: str) -> tuple[int, int]:
    """`Ctrl+Shift+F` 形式を Windows の修飾子と仮想キーコードへ変換する。"""
    parts = [part.strip().lower() for part in combo.split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError(f"ホットキー文字列の形式が不正です: {combo!r}")

    modifiers = 0
    key_part = parts[-1]
    for modifier in parts[:-1]:
        if modifier not in _MODIFIER_MAP:
            raise ValueError(f"不明な修飾キーです: {modifier!r}")
        modifiers |= _MODIFIER_MAP[modifier]

    if len(key_part) != 1 or not key_part.isalnum():
        raise ValueError(f"対応していない主キーです: {key_part!r}")
    return modifiers, ord(key_part.upper())


def format_hotkey(modifiers: int, vk_code: int) -> str:
    """Windows の修飾子と仮想キーコードを正規化したキー文字列へ変換する。"""
    parts: list[str] = []
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
    """複数の Windows グローバルホットキーを単一スレッドで待ち受ける。"""

    def __init__(self, tk_root: tk.Tk, on_triggered: Callable[[int], None]) -> None:
        self.tk_root = tk_root
        self.on_triggered = on_triggered
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._running = False

    def start(self, modifiers: int, vk_code: int) -> bool:
        """従来の単一登録 Interface を維持する。"""
        return self.start_many(
            [HotkeyRegistration(GLOBAL_HOTKEY_ID, modifiers, vk_code)]
        )

    def start_many(self, registrations: Iterable[HotkeyRegistration]) -> bool:
        """登録集合を置き換える。いずれかが失敗した場合は全件を解除する。"""
        entries = list(registrations)
        if len({entry.hotkey_id for entry in entries}) != len(entries):
            logger.error("重複したホットキーIDが指定されました。")
            return False
        if not entries:
            self.stop()
            return True
        if sys.platform != "win32":
            logger.warning(
                "Windows 以外の環境のため、グローバルホットキー登録をスキップします。"
            )
            return False

        self.stop()
        import ctypes.wintypes

        result_holder: dict[str, bool] = {}
        ready_event = threading.Event()

        def _run() -> None:
            user32 = ctypes.windll.user32
            self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
            registered_ids: list[int] = []
            try:
                for entry in entries:
                    registered = user32.RegisterHotKey(
                        None,
                        entry.hotkey_id,
                        entry.modifiers | MOD_NOREPEAT,
                        entry.vk_code,
                    )
                    if not registered:
                        logger.warning(
                            "グローバルホットキーの登録に失敗しました（ID: %s、キー競合の可能性）。",
                            entry.hotkey_id,
                        )
                        for hotkey_id in reversed(registered_ids):
                            user32.UnregisterHotKey(None, hotkey_id)
                        result_holder["ok"] = False
                        ready_event.set()
                        return
                    registered_ids.append(entry.hotkey_id)

                self._running = True
                result_holder["ok"] = True
                ready_event.set()
                message = ctypes.wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(message), None, 0, 0) != 0:
                    if message.message == WM_HOTKEY:
                        self.tk_root.after(0, self.on_triggered, int(message.wParam))
            finally:
                for hotkey_id in reversed(registered_ids):
                    user32.UnregisterHotKey(None, hotkey_id)
                self._running = False

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        ready_event.wait(timeout=1.0)
        return result_holder.get("ok", False)

    def stop(self) -> None:
        """メッセージループを停止し、登録済みの全キーを解放する。"""
        if sys.platform == "win32" and self._thread_id is not None:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._thread_id = None
        self._running = False
