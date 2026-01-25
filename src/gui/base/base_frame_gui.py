from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Any

from src.utils.error_handler import log_and_show_error

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication


class BaseFrameGUI(tk.Frame):
    def __init__(
        self, master: tk.Misc, app_instance: BaseApplication, **kwargs: Any
    ) -> None:
        super().__init__(master, **kwargs)
        self.master = master
        self.app = app_instance
        self.log_and_show_error = log_and_show_error

    # Placeholder for common widget creation or layout methods
    def _create_common_widgets(self) -> None:
        pass
