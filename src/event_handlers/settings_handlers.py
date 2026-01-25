from __future__ import annotations

from typing import TYPE_CHECKING

from .base_event_handler import BaseEventHandler

if TYPE_CHECKING:
    from src.core.config.settings_manager import SettingsManager
    from src.core.event_dispatcher import EventDispatcher


class SettingsEventHandlers(BaseEventHandler):
    def __init__(self, event_dispatcher: EventDispatcher, settings_manager: SettingsManager) -> None:
        self.settings_manager = settings_manager
        super().__init__(event_dispatcher)

    def _register_handlers(self) -> None:
        self.subscribe("SETTINGS_ALWAYS_ON_TOP", self.handle_set_always_on_top)
        self.subscribe("SETTINGS_SET_THEME", self.handle_set_theme) # Added this missing subscription

    def handle_set_always_on_top(self, value: bool) -> None:
        self.settings_manager.set_setting("always_on_top", value)
        self.settings_manager.save_settings()

    def handle_set_theme(self, theme_name: str, save: bool = True) -> None:
        self.settings_manager.set_setting("theme", theme_name)
        if save:
            self.settings_manager.save_settings()
        else:
            self.settings_manager.notify_listeners()
