from __future__ import annotations
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.event_dispatcher import EventDispatcher
    from src.core.config.settings_manager import SettingsManager


class SettingsEventHandlers:
    def __init__(self, event_dispatcher: "EventDispatcher", settings_manager: "SettingsManager"):
        self.event_dispatcher = event_dispatcher
        self.settings_manager = settings_manager
        self.event_dispatcher.subscribe("SETTINGS_ALWAYS_ON_TOP", self.handle_set_always_on_top)

    def handle_set_always_on_top(self, value: bool):
        self.settings_manager.set_setting("always_on_top", value)
        self.settings_manager.save_settings()

    def handle_set_theme(self, theme_name: str, save: bool = True):
        self.settings_manager.set_setting("theme", theme_name)
        if save:
            self.settings_manager.save_settings()
        else:
            self.settings_manager.notify_listeners()
