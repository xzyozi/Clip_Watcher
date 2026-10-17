from __future__ import annotations

import logging
from typing import Any

from src.core.platform.errors import UnsupportedFeatureError
from src.core.platform.services import PlatformServices

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(
        self,
        platform_services: PlatformServices,
        initial_settings: dict[str, Any] | None = None,
    ) -> None:
        self.platform_services = platform_services
        self.settings: dict[str, Any] = (
            initial_settings if initial_settings is not None else {}
        )

    def update_settings(self, new_settings: dict[str, Any]) -> None:
        self.settings = new_settings

    def play_notification_sound(self) -> None:
        if not self.settings.get("notification_sound_enabled"):
            return

        try:
            sound_player = self.platform_services.sound_player()
        except UnsupportedFeatureError as e:
            logger.debug("通知音は非対応のため、ビープ音をスキップしました: %s", e)
            return

        try:
            sound_player.play_notification_beep(1000, 200)
        except Exception as e:
            logger.warning("通知音の再生に失敗しました: %s", e, exc_info=True)
