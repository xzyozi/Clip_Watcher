from src.event_dispatcher import EventDispatcher

class SettingsEventHandlers:
    def __init__(self, event_dispatcher: EventDispatcher):
        self.event_dispatcher = event_dispatcher

        # Subscribe to events
        self.event_dispatcher.subscribe("SETTINGS_ALWAYS_ON_TOP", self.handle_always_on_top)
        self.event_dispatcher.subscribe("SETTINGS_SET_THEME", self.handle_set_theme)

    def handle_always_on_top(self, always_on_top):
        self.event_dispatcher.dispatch("REQUEST_ALWAYS_ON_TOP", always_on_top)

    def handle_set_theme(self, theme_name):
        self.event_dispatcher.dispatch("REQUEST_SET_THEME", theme_name)