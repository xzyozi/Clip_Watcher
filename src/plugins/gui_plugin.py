from __future__ import annotations

from abc import abstractmethod
from tkinter import ttk
from typing import TYPE_CHECKING

from src.plugins.base_plugin import Plugin

if TYPE_CHECKING:
    from src.core.bootstrap.base_application import BaseApplication


class GuiPlugin(Plugin):
    """Tk GUIを提供するプラグインの基底クラス。"""

    def has_gui_component(self) -> bool:
        """このプラグインがGUIコンポーネントを提供することを示す。"""
        return True

    @abstractmethod
    def create_gui_component(
        self, parent: ttk.Notebook, app_instance: BaseApplication
    ) -> ttk.Frame | None:
        """親Notebookに追加するGUIコンポーネントを生成する。"""
        raise NotImplementedError
