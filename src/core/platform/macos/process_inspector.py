"""src/core/platform/macos/process_inspector.py

macOS 用のアクティブウィンドウ・プロセス情報検査実装。
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def _get_active_process_via_appkit() -> str | None:
    """AppKit (ctypes経由) を使用して最前面アプリケーションの名前を取得する。"""
    try:
        appkit_path = ctypes.util.find_library("AppKit")
        objc_path = ctypes.util.find_library("objc")
        if not appkit_path or not objc_path:
            return None

        appkit = ctypes.cdll.LoadLibrary(appkit_path)  # noqa: F841
        objc = ctypes.cdll.LoadLibrary(objc_path)

        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]

        ns_workspace_cls = objc.objc_getClass(b"NSWorkspace")
        if not ns_workspace_cls:
            return None

        shared_workspace_sel = objc.sel_registerName(b"sharedWorkspace")
        frontmost_app_sel = objc.sel_registerName(b"frontmostApplication")
        localized_name_sel = objc.sel_registerName(b"localizedName")
        utf8_string_sel = objc.sel_registerName(b"UTF8String")

        # id objc_msgSend(id self, SEL op)
        c_msg_send = ctypes.cast(
            objc.objc_msgSend,
            ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p),
        )

        ws = c_msg_send(ns_workspace_cls, shared_workspace_sel)
        if not ws:
            return None

        app = c_msg_send(ws, frontmost_app_sel)
        if not app:
            return None

        name_ns = c_msg_send(app, localized_name_sel)
        if not name_ns:
            return None

        # const char * objc_msgSend(id self, SEL op)
        c_msg_send_str = ctypes.cast(
            objc.objc_msgSend,
            ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p),
        )

        name_bytes = c_msg_send_str(name_ns, utf8_string_sel)
        if name_bytes:
            return str(name_bytes.decode("utf-8"))
    except Exception as e:
        logger.debug("AppKit 経由のプロセス名取得に失敗: %s", e)
    return None


def _get_active_process_via_osascript(timeout: float = 1.0) -> str | None:
    """osascript コマンドを使用して最前面アプリケーションの名前を取得するフォールバック。"""
    try:
        res = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of first application process whose frontmost is true',
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if res.returncode == 0:
            name = res.stdout.strip()
            if name:
                return name
    except Exception as e:
        logger.debug("osascript 経由のプロセス名取得に失敗: %s", e)
    return None


class MacOSProcessInspector:
    """macOS 用のアクティブプロセス情報検査実装。

    AppKit (ctypes) を優先し、必要に応じて osascript にフォールバックする。
    ゼロインストール原則に従い、PyObjC などの外部依存は追加しない。
    """

    def get_active_process_name(self) -> str | None:
        """現在前面にあるアプリケーション名（例: "iTerm2", "Google Chrome"）を返す。"""
        if sys.platform != "darwin":
            return None

        name = _get_active_process_via_appkit()
        if name:
            return name

        return _get_active_process_via_osascript()
