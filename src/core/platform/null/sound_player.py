"""src/core/platform/null/sound_player.py

非 Windows / ヘッドレス環境向けの Null（消音）サウンドプレイヤー。
"""

from __future__ import annotations


class NullSoundPlayer:
    """非対応環境向けのダミー効果音再生クラス。"""

    def play_notification_beep(
        self, frequency: int = 1000, duration_ms: int = 200
    ) -> bool:
        return True
