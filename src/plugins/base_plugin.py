from abc import ABC, abstractmethod

class Plugin(ABC):
    """
    A base class for all plugins.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """A user-friendly name for the plugin."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the plugin does."""
        pass

    @abstractmethod
    def process(self, text: str) -> str:
        """
        Process the input text and return the modified text.
        If the plugin cannot process the text, it should return the original text.
        """
        pass
