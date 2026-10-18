"""src/core/platform/linux/process_inspector.py

Linux 用のアクティブウィンドウ・プロセス情報検査実装。
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_WINDOW_ID_PATTERN = re.compile(r"0x[0-9a-fA-F]+")
_PID_PATTERN = re.compile(r"\b\d+\b")
_WM_CLASS_PATTERN = re.compile(r'"([^"]+)"')


def _get_active_process_via_xprop(timeout: float = 1.0) -> str | None:
    """xprop を利用して最前面ウィンドウのプロセス名または WM_CLASS を取得する。"""
    try:
        # 1. アクティブウィンドウ ID を取得
        res = subprocess.run(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if res.returncode != 0:
            return None

        match = _WINDOW_ID_PATTERN.search(res.stdout)
        if not match:
            return None
        win_id = match.group(0)
        if win_id == "0x0":
            return None

        # 2. _NET_WM_PID によるプロセス PID の取得を試みる
        pid_res = subprocess.run(
            ["xprop", "-id", win_id, "_NET_WM_PID"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if pid_res.returncode == 0:
            pid_match = _PID_PATTERN.search(pid_res.stdout)
            if pid_match:
                pid = pid_match.group(0)
                comm_path = Path(f"/proc/{pid}/comm")
                if comm_path.exists():
                    comm_name = comm_path.read_text(encoding="utf-8").strip()
                    if comm_name:
                        return comm_name

        # 3. PID が取れない場合は WM_CLASS を取得
        class_res = subprocess.run(
            ["xprop", "-id", win_id, "WM_CLASS"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if class_res.returncode == 0:
            classes = _WM_CLASS_PATTERN.findall(class_res.stdout)
            if classes:
                # WM_CLASS は 通常 [instance_name, class_name] を返す
                return str(classes[-1])
    except Exception as e:
        logger.debug("xprop 経由のプロセス名取得に失敗: %s", e)
    return None


class LinuxProcessInspector:
    """Linux 用のアクティブプロセス情報検査実装。

    X11 環境で xprop を使用して最前面プロセスの名前を取得する。
    Wayland 環境や xprop 未導入環境では安全に None を返す。
    """

    def get_active_process_name(self) -> str | None:
        """現在前面にあるウィンドウのプロセス名またはクラス名を返す。"""
        if not sys.platform.startswith("linux"):
            return None

        return _get_active_process_via_xprop()
