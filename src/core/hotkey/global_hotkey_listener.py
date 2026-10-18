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
    "opt": MOD_ALT,
    "option": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "super": MOD_WIN,
    "cmd": MOD_WIN,
    "command": MOD_WIN,
}

# macOS Carbon HotKey 修飾キー定数
DARWIN_CMD = 0x0100
DARWIN_SHIFT = 0x0200
DARWIN_OPT = 0x0800
DARWIN_CTRL = 0x1000

_DARWIN_MODIFIER_MAP = {
    "cmd": DARWIN_CMD,
    "command": DARWIN_CMD,
    "win": DARWIN_CMD,
    "super": DARWIN_CMD,
    "shift": DARWIN_SHIFT,
    "opt": DARWIN_OPT,
    "option": DARWIN_OPT,
    "alt": DARWIN_OPT,
    "ctrl": DARWIN_CTRL,
    "control": DARWIN_CTRL,
}

# macOS Carbon ANSI 仮想キーコード
_DARWIN_KEY_MAP = {
    "A": 0,
    "B": 11,
    "C": 8,
    "D": 2,
    "E": 14,
    "F": 3,
    "G": 5,
    "H": 4,
    "I": 34,
    "J": 38,
    "K": 40,
    "L": 37,
    "M": 46,
    "N": 45,
    "O": 31,
    "P": 35,
    "Q": 12,
    "R": 15,
    "S": 1,
    "T": 17,
    "U": 32,
    "V": 9,
    "W": 13,
    "X": 7,
    "Y": 16,
    "Z": 6,
    "0": 29,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "5": 23,
    "6": 22,
    "7": 26,
    "8": 28,
    "9": 25,
}
_DARWIN_VK_TO_KEY = {v: k for k, v in _DARWIN_KEY_MAP.items()}


# GetMessageW の戻り値を分類した結果。
# - "error"    : -1（API エラー）。ループを抜ける必要がある。
# - "quit"     : 0（WM_QUIT）。正常にループを抜ける。
# - "dispatch" : 正の値。メッセージを処理してループを継続する。
GET_MESSAGE_ERROR = "error"
GET_MESSAGE_QUIT = "quit"
GET_MESSAGE_DISPATCH = "dispatch"


def classify_get_message_result(ret: int) -> str:
    """GetMessageW の戻り値を分類する純粋関数。

    Windows API の GetMessageW は成功時に正の値、WM_QUIT で 0、エラー時に -1 を返す。
    従来の "!= 0" 判定では -1（エラー）でループを抜けられず、無限ループに陥り
    CPU を枯渇させていた（#112）。この関数で戻り値の意味を一元的に判定する。
    """
    if ret == -1:
        return GET_MESSAGE_ERROR
    if ret == 0:
        return GET_MESSAGE_QUIT
    return GET_MESSAGE_DISPATCH


@dataclass(frozen=True)
class HotkeyRegistration:
    """ホットキーの不変な定義。"""

    hotkey_id: int
    modifiers: int
    vk_code: int


def parse_hotkey_string(combo: str, platform: str | None = None) -> tuple[int, int]:
    """`Ctrl+Shift+F` または `Cmd+Shift+F` 形式を修飾子と仮想キーコードへ変換する。"""
    target_platform = platform if platform is not None else sys.platform
    parts = [part.strip().lower() for part in combo.split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError(f"ホットキー文字列の形式が不正です: {combo!r}")

    modifiers = 0
    key_part = parts[-1]

    if target_platform == "darwin":
        for modifier in parts[:-1]:
            if modifier not in _DARWIN_MODIFIER_MAP:
                raise ValueError(f"不明な修飾キーです: {modifier!r}")
            modifiers |= _DARWIN_MODIFIER_MAP[modifier]

        key_upper = key_part.upper()
        if key_upper not in _DARWIN_KEY_MAP:
            raise ValueError(f"対応していない主キーです: {key_part!r}")
        return modifiers, _DARWIN_KEY_MAP[key_upper]

    for modifier in parts[:-1]:
        if modifier not in _MODIFIER_MAP:
            raise ValueError(f"不明な修飾キーです: {modifier!r}")
        modifiers |= _MODIFIER_MAP[modifier]

    if len(key_part) != 1 or not key_part.isalnum():
        raise ValueError(f"対応していない主キーです: {key_part!r}")
    return modifiers, ord(key_part.upper())


def format_hotkey(modifiers: int, vk_code: int, platform: str | None = None) -> str:
    """修飾子と仮想キーコードを正規化したキー文字列へ変換する。"""
    target_platform = platform if platform is not None else sys.platform
    parts: list[str] = []

    if target_platform == "darwin":
        if modifiers & DARWIN_CMD:
            parts.append("Cmd")
        if modifiers & DARWIN_CTRL:
            parts.append("Ctrl")
        if modifiers & DARWIN_OPT:
            parts.append("Opt")
        if modifiers & DARWIN_SHIFT:
            parts.append("Shift")
        key_str = _DARWIN_VK_TO_KEY.get(vk_code)
        if key_str:
            parts.append(key_str)
        else:
            parts.append(chr(vk_code))
        return "+".join(parts)

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
                while True:
                    ret = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                    result = classify_get_message_result(ret)
                    if result == GET_MESSAGE_ERROR:
                        last_error = ctypes.windll.kernel32.GetLastError()
                        logger.error(
                            "GetMessageW がエラー (-1) を返しました "
                            "(GetLastError=%s)。ホットキー用メッセージループを終了します。",
                            last_error,
                        )
                        break
                    if result == GET_MESSAGE_QUIT:  # WM_QUIT（正常終了）
                        break
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
