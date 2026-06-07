from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from reusable_gui.interfaces import GUIContextProto


class BaseToplevelGUI(tk.Toplevel):
    def __init__(
        self, master: tk.Misc, app_instance: GUIContextProto, **kwargs: Any
    ) -> None:
        super().__init__(master, **kwargs)
        self.master = master
        self.app = app_instance
        if hasattr(self.app.theme_manager, "apply_theme_to_toplevel"):
            self.app.theme_manager.apply_theme_to_toplevel(self)  # type: ignore

    # Placeholder for common widget creation or layout methods
    def _create_common_widgets(self) -> None:
        pass
