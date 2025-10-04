import winsound
import logging

from src.utils.error_handler import log_and_show_error

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, initial_settings=None):
        self.settings = initial_settings if initial_settings is not None else {}

    def update_settings(self, new_settings):
        self.settings = new_settings

    def play_notification_sound(self):
        if self.settings.get("notification_sound_enabled"):
            try:
                winsound.Beep(1000, 200) # 1000Hz for 200ms
            except Exception as e:
                log_and_show_error("エラー",f"Error playing sound: {e}", exc_info=True)
