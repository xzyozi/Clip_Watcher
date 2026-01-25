from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any

from src.core.config.defaults import THEMES

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication


class BaseToplevelGUI(tk.Toplevel):
    def __init__(
        self, master: tk.Misc, app_instance: BaseApplication, **kwargs: Any
    ) -> None:
        super().__init__(master, **kwargs)
        self.master = master
        self.app = app_instance
        self.app.theme_manager.apply_theme_to_widget_tree( # type: ignore
            self, THEMES[self.app.theme_manager.get_current_theme()] # type: ignore
        )

    # Placeholder for common widget creation or layout methods
    def _create_common_widgets(self) -> None:
        pass
