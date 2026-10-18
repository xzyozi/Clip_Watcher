"""src/core/platform/macos/paste_sender.py

macOS 用のアクティブウィンドウへの貼り付けキーストローク送信実装。
"""

from __future__ import annotations

import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


class MacOSPasteSender:
    """macOS 用の Cmd+V キーストローク送信アダプター。"""

    def are_modifiers_released(self) -> bool:
        """修飾キーの解放状態判定。"""
        return True

    def paste_active_window(self) -> bool:
        """最前面ウィンドウへ Cmd+V を送信する。"""
        if sys.platform != "darwin":
            return False

        try:
            res = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to keystroke "v" using command down',
                ],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )
            if res.returncode == 0:
                logger.debug("macOS Cmd+V 貼り付けキーストロークを送信しました。")
                return True
            logger.debug("osascript キーストローク送信エラー: %s", res.stderr)
            return False
        except Exception as e:
            logger.debug("macOS 貼り付け送信に失敗しました: %s", e)
            return False
