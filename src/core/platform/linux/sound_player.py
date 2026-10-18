"""src/core/platform/linux/sound_player.py

Linux 用のシステムサウンド / ターミナルベル通知音再生実装。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_LINUX_SOUNDS = [
    Path("/usr/share/sounds/freedesktop/stereo/bell.oga"),
    Path("/usr/share/sounds/freedesktop/stereo/complete.oga"),
    Path("/usr/share/sounds/sound-icons/prompt.wav"),
]


class LinuxSoundPlayer:
    """Linux 用の通知音再生実装。

    paplay, canberra-gtk-play, aplay の順で利用可能な再生コマンドを探し、
    システムサウンドを再生する。見つからない場合はターミナルベルを使用する。
    """

    def __init__(self, sound_file_path: Path | str | None = None) -> None:
        if sound_file_path:
            self._sound_path: Path | None = Path(sound_file_path)
        else:
            self._sound_path = self._resolve_default_sound()

    @staticmethod
    def _resolve_default_sound() -> Path | None:
        for p in _DEFAULT_LINUX_SOUNDS:
            if p.exists():
                return p
        return None

    def play_notification_beep(
        self, frequency: int = 1000, duration_ms: int = 200
    ) -> bool:
        """システム通知音を再生する。"""
        if not sys.platform.startswith("linux"):
            return False

        # 1. paplay (PulseAudio / PipeWire)
        if shutil.which("paplay") and self._sound_path and self._sound_path.exists():
            try:
                subprocess.Popen(
                    ["paplay", str(self._sound_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception as e:
                logger.debug("paplay 再生失敗: %s", e)

        # 2. canberra-gtk-play
        if shutil.which("canberra-gtk-play"):
            try:
                subprocess.Popen(
                    ["canberra-gtk-play", "-i", "bell"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception as e:
                logger.debug("canberra-gtk-play 再生失敗: %s", e)

        # 3. aplay (ALSA)
        if (
            shutil.which("aplay")
            and self._sound_path
            and str(self._sound_path).endswith(".wav")
        ):
            try:
                subprocess.Popen(
                    ["aplay", str(self._sound_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception as e:
                logger.debug("aplay 再生失敗: %s", e)

        # 4. フォールバック: ターミナルベル
        try:
            sys.stdout.write("\a")
            sys.stdout.flush()
            return True
        except Exception as e:
            logger.debug("ターミナルベル再生失敗: %s", e)
            return False
