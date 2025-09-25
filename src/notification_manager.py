import winsound
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager

    def play_notification_sound(self):
        if self.settings_manager.get_setting("notification_sound_enabled"):
            try:
                winsound.Beep(1000, 200) # 1000Hz for 200ms
            except Exception as e:
                logger.error(f"Error playing sound: {e}", exc_info=True)