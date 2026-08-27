from __future__ import annotations

import ctypes
import logging
import sys
from typing import Protocol

logger = logging.getLogger(__name__)

_VK_SHIFT = 0x10
_VK_CONTROL = 0x11
_VK_MENU = 0x12
_VK_LWIN = 0x5B
_VK_RWIN = 0x5C
_VK_V = 0x56
_KEYEVENTF_KEYUP = 0x0002
_MODIFIER_KEYS = (_VK_SHIFT, _VK_CONTROL, _VK_MENU, _VK_LWIN, _VK_RWIN)


class PasteSender(Protocol):
    """アクティブウィンドウへ貼り付け操作を送る Interface。"""

    def paste_active_window(self) -> bool: ...


class WindowsPasteSender:
    """Windows の入力ストリームへCtrl+Vを送るアダプター。"""

    def are_modifiers_released(self) -> bool:
        """物理修飾キーがすべて解放済みならTrueを返す。"""
        if sys.platform != "win32":
            return False
        try:
            user32 = ctypes.windll.user32
            return all(
                not user32.GetAsyncKeyState(virtual_key) & 0x8000
                for virtual_key in _MODIFIER_KEYS
            )
        except OSError:
            logger.exception("修飾キー状態の取得に失敗しました。")
            return False

    def paste_active_window(self) -> bool:
        if sys.platform != "win32":
            logger.warning("Windows 以外の環境では自動貼り付けを実行できません。")
            return False
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(_VK_CONTROL, 0, 0, 0)
            user32.keybd_event(_VK_V, 0, 0, 0)
            user32.keybd_event(_VK_V, 0, _KEYEVENTF_KEYUP, 0)
            user32.keybd_event(_VK_CONTROL, 0, _KEYEVENTF_KEYUP, 0)
            return True
        except OSError:
            logger.exception("自動貼り付けのキーストローク送信に失敗しました。")
            return False
