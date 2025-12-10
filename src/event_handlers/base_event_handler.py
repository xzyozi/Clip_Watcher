from abc import ABC, abstractmethod
from typing import Callable

if TYPE_CHECKING:
    from src.core.event_dispatcher import EventDispatcher

class BaseEventHandler(ABC):
    """A base class for event handlers to standardize subscription and cleanup."""
    
    def __init__(self, dispatcher: 'EventDispatcher'):
        """
        Initializes the event handler.

        Args:
            dispatcher: The event dispatcher to subscribe to.
        """
        self.dispatcher = dispatcher
        self._subscriptions = []
        self._register_handlers()

    @abstractmethod
    def _register_handlers(self) -> None:
        """
        A method to register all event handlers for this class.
        This is where `self.subscribe()` should be called.
        """
        pass

    def subscribe(self, event_name: str, handler: Callable) -> None:
        """
        Subscribes a handler to an event and tracks the subscription.

        Args:
            event_name: The name of the event to subscribe to.
            handler: The function to call when the event is dispatched.
        """
        self.dispatcher.subscribe(event_name, handler)
        self._subscriptions.append((event_name, handler))

    def cleanup(self) -> None:
        """
        Unsubscribes all handlers that were registered through this instance.
        This is useful for preventing memory leaks when a handler is no longer needed.
        """
        for event_name, handler in self._subscriptions:
            # Assuming the dispatcher has an 'unsubscribe' method
            if hasattr(self.dispatcher, 'unsubscribe'):
                self.dispatcher.unsubscribe(event_name, handler)
        self._subscriptions = []
