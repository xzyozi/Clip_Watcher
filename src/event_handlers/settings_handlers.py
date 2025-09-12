class SettingsEventHandlers:
    def __init__(self, app_instance):
        self.app = app_instance

    def handle_always_on_top(self):
        always_on_top = self.app.always_on_top_var.get()
        self.app.master.attributes('-topmost', always_on_top)
        print(f"Always on Top set to: {always_on_top}")

    def handle_set_theme(self, theme_name):
        self.app.gui.apply_theme(theme_name)
        print(f"Theme set to: {theme_name}")