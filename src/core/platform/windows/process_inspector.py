"""src/core/platform/windows/process_inspector.py

Windows 用のアクティブウィンドウ・プロセス情報検査実装。
"""

from __future__ import annotations

import ctypes
import logging
import sys

if sys.platform == "win32":
    import ctypes.wintypes

logger = logging.getLogger(__name__)


class WindowsProcessInspector:
    """Win32 API (user32, kernel32, psapi) を利用したプロセス名取得実装。"""

    def get_active_process_name(self) -> str | None:
        """現在前面にあるウィンドウの実行ファイル名（小文字・大文字の区別なし比較用）を返す。"""
        if sys.platform != "win32":
            return None

        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi

            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None

            pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            process_handle = kernel32.OpenProcess(0x0410, False, pid.value)
            if not process_handle:
                return None

            exe_name = (ctypes.c_char * 260)()
            psapi.GetModuleBaseNameA(process_handle, None, exe_name, 260)
            kernel32.CloseHandle(process_handle)

            return exe_name.value.decode(errors="ignore")
        except Exception as e:
            logger.debug("Windows プロセス名の取得に失敗しました: %s", e)
            return None
