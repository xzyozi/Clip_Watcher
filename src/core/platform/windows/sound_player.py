"""src/core/platform/windows/sound_player.py

Windows 用の winsound.Beep を使用した通知音再生実装。
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


class WindowsSoundPlayer:
    """Windows の winsound API を用いた通知音再生。"""

    def play_notification_beep(
        self, frequency: int = 1000, duration_ms: int = 200
    ) -> bool:
        """指定周波数・長さでビープ音を再生する。"""
        if sys.platform != "win32":
            return False

        try:
            import winsound

            winsound.Beep(frequency, duration_ms)
            return True
        except Exception as e:
            logger.debug("winsound.Beep の再生に失敗しました: %s", e)
            return False
