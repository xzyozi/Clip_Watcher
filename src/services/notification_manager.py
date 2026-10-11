from __future__ import annotations

import logging
import sys
from typing import Any

from src.utils.error_handler import log_and_show_error

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    try:
        import winsound
    except ImportError:
        winsound = None  # type: ignore[assignment]
else:
    winsound = None  # type: ignore[assignment]


class NotificationManager:
    def __init__(self, initial_settings: dict[str, Any] | None = None) -> None:
        self.settings: dict[str, Any] = (
            initial_settings if initial_settings is not None else {}
        )

    def update_settings(self, new_settings: dict[str, Any]) -> None:
        self.settings = new_settings

    def play_notification_sound(self) -> None:
        if self.settings.get("notification_sound_enabled"):
            if winsound is not None:
                try:
                    winsound.Beep(1000, 200)  # 1000Hz for 200ms
                except Exception as e:
                    log_and_show_error(
                        "エラー", f"Error playing sound: {e}", exc_info=True
                    )
            else:
                logger.debug(
                    "プラットフォーム非互換または winsound 利用不可のため、ビープ音をスキップしました。"
                )
