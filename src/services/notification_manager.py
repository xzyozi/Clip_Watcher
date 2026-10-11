from __future__ import annotations

import logging
import sys
from typing import Any

from src.core.platform.protocols import SoundPlayer
from src.utils.error_handler import log_and_show_error

logger = logging.getLogger(__name__)


def _create_default_sound_player() -> SoundPlayer | None:
    if sys.platform == "win32":
        try:
            from src.core.platform.windows.sound_player import WindowsSoundPlayer

            return WindowsSoundPlayer()
        except ImportError:
            return None
    return None


class NotificationManager:
    def __init__(
        self,
        initial_settings: dict[str, Any] | None = None,
        sound_player: SoundPlayer | None = None,
    ) -> None:
        self.settings: dict[str, Any] = (
            initial_settings if initial_settings is not None else {}
        )
        self.sound_player: SoundPlayer | None = (
            sound_player if sound_player is not None else _create_default_sound_player()
        )

    def update_settings(self, new_settings: dict[str, Any]) -> None:
        self.settings = new_settings

    def play_notification_sound(self) -> None:
        if self.settings.get("notification_sound_enabled"):
            if self.sound_player is not None:
                try:
                    self.sound_player.play_notification_beep(1000, 200)
                except Exception as e:
                    log_and_show_error(
                        "エラー", f"Error playing sound: {e}", exc_info=True
                    )
            else:
                logger.debug(
                    "サウンドプレイヤー未設定または非対応のため、ビープ音をスキップしました。"
                )
