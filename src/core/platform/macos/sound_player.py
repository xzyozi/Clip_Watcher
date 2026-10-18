"""src/core/platform/macos/sound_player.py

macOS 用の afplay コマンドを使用した通知音再生実装。
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_SOUNDS = [
    Path("/System/Library/Sounds/Tink.aiff"),
    Path("/System/Library/Sounds/Pop.aiff"),
    Path("/System/Library/Sounds/Ping.aiff"),
]


class MacOSSoundPlayer:
    """macOS の afplay コマンドを用いた通知音再生。"""

    def __init__(self, sound_file_path: Path | str | None = None) -> None:
        if sound_file_path:
            self._sound_path: Path | None = Path(sound_file_path)
        else:
            self._sound_path = self._resolve_default_sound()

    @staticmethod
    def _resolve_default_sound() -> Path | None:
        for p in _DEFAULT_SOUNDS:
            if p.exists():
                return p
        return None

    def play_notification_beep(
        self, frequency: int = 1000, duration_ms: int = 200
    ) -> bool:
        """システム通知音を再生する。

        macOS の afplay は任意の周波数指定は受け付けないため、
        標準の短いシステムサウンド（Tink/Pop等）を再生する。
        """
        if sys.platform != "darwin":
            return False

        if not self._sound_path or not self._sound_path.exists():
            logger.debug("macOS サウンドファイルが見つかりません。")
            return False

        try:
            # UI をブロックしないよう非同期 (Popen) で再生する
            subprocess.Popen(
                ["/usr/bin/afplay", str(self._sound_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.debug("afplay による通知音再生に失敗しました: %s", e)
            return False
