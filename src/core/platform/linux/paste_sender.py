"""src/core/platform/linux/paste_sender.py

Linux 用のアクティブウィンドウへの貼り付けキーストローク送信実装。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)


class LinuxPasteSender:
    """Linux 用の xdotool を用いた Ctrl+V 送信アダプター。"""

    def are_modifiers_released(self) -> bool:
        """修飾キーの解放状態判定。"""
        return True

    def paste_active_window(self) -> bool:
        """最前面ウィンドウへ Ctrl+V を送信する。"""
        if not sys.platform.startswith("linux"):
            return False

        if not shutil.which("xdotool"):
            logger.debug("xdotool が見つからないため自動貼り付けをスキップします。")
            return False

        try:
            res = subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )
            return res.returncode == 0
        except Exception as e:
            logger.debug("Linux 貼り付け送信に失敗しました: %s", e)
            return False
