from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, overload

if TYPE_CHECKING:
    from src.core.events.event_dispatcher import EventDispatcher


class BaseEventHandler(ABC):
    """A base class for event handlers to standardize subscription and cleanup."""

    def __init__(self, dispatcher: "EventDispatcher") -> None:
        """
        Initializes the event handler.

        Args:
            dispatcher: The event dispatcher to subscribe to.
        """
        self.dispatcher = dispatcher
        self._subscriptions: list[tuple[str, Callable[..., Any]]] = []
        self._register_handlers()

    @abstractmethod
    def _register_handlers(self) -> None:
        """
        A method to register all event handlers for this class.
        This is where `self.subscribe()` should be called.
        """
        pass

    @overload
    def subscribe(
        self,
        event_name: Literal["SETTINGS_CHANGED"],
        handler: Callable[[dict[str, Any]], Any],
    ) -> None: ...

    @overload
    def subscribe(
        self,
        event_name: Literal["HISTORY_UPDATED"],
        handler: Callable[[list[dict[str, Any]]], Any],
    ) -> None: ...

    @overload
    def subscribe(
        self, event_name: Literal["LANGUAGE_CHANGED"], handler: Callable[[str], Any]
    ) -> None: ...

    @overload
    def subscribe(
        self,
        event_name: Literal["HISTORY_ITEM_EDITED"],
        handler: Callable[[dict[str, Any]], Any],
    ) -> None: ...

    @overload
    def subscribe(
        self,
        event_name: Literal["REQUEST_UNDO_LAST_ACTION", "REQUEST_REDO_LAST_ACTION"],
        handler: Callable[[], Any],
    ) -> None: ...

    @overload
    def subscribe(self, event_name: str, handler: Callable[..., Any]) -> None: ...

    def subscribe(self, event_name: str, handler: Callable[..., Any]) -> None:
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
            if hasattr(self.dispatcher, "unsubscribe"):
                self.dispatcher.unsubscribe(event_name, handler)
        self._subscriptions = []
