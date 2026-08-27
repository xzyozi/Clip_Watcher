from __future__ import annotations

import ctypes
import logging
import sys
from typing import Protocol

logger = logging.getLogger(__name__)

_VK_CONTROL = 0x11
_VK_V = 0x56
_KEYEVENTF_KEYUP = 0x0002


class PasteSender(Protocol):
    """アクティブウィンドウへ貼り付け操作を送る Interface。"""

    def paste_active_window(self) -> bool: ...


class WindowsPasteSender:
    """Windows の入力ストリームへ Ctrl+V を送るアダプター。"""

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
