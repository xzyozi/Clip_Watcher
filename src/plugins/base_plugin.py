from abc import ABC, abstractmethod
import tkinter as tk
from tkinter import ttk


class Plugin(ABC):
    """
    A base class for all plugins.
    Plugins can either process text or provide a GUI component, or both.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """A user-friendly name for the plugin, used for menus or tab titles."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the plugin does."""
        pass

    def process(self, text: str) -> str:
        """
        Process the input text and return the modified text.
        If the plugin cannot process the text, it should raise NotImplementedError.
        """
        raise NotImplementedError

    def has_gui_component(self) -> bool:
        """
        Returns True if this plugin provides a GUI component.
        Defaults to False.
        """
        return False

    def create_gui_component(self, parent: ttk.Notebook, app_instance) -> ttk.Frame | None:
        """
        Creates and returns the GUI component for this plugin.
        This method should be overridden by plugins that provide a GUI.
        """
        return None
