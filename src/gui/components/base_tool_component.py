from abc import ABC, abstractmethod
from src.gui.base.base_frame_gui import BaseFrameGUI

class BaseToolComponent(BaseFrameGUI, ABC):
    """
    A base class for all GUI tool components that can be loaded into tabs.
    """
    @property
    @abstractmethod
    def tool_name(self) -> str:
        """
        A user-friendly name for the tool, used for the tab title.
        """
        pass
