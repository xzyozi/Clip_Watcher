from __future__ import annotations
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.event_dispatcher import EventDispatcher
    from src.core.settings_manager import SettingsManager


class SettingsEventHandlers:
    def __init__(self, event_dispatcher: "EventDispatcher", settings_manager: "SettingsManager"):
        self.event_dispatcher = event_dispatcher
        self.settings_manager = settings_manager

    def handle_set_theme(self, theme_name: str):
        self.settings_manager.set_setting("theme", theme_name)
        self.settings_manager.save_settings()
