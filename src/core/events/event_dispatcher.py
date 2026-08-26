import logging
import traceback
from collections import defaultdict
from collections.abc import Callable
from typing import Any, Literal, overload

from src.utils.error_handler import log_and_show_error

logger = logging.getLogger(__name__)


def _get_listener_name(listener: Callable[..., Any]) -> str:
    """安全にリスナーの表示名を取得します（functools.partial や callable オブジェクト対応）。"""
    if hasattr(listener, "__qualname__"):
        return str(listener.__qualname__)
    if hasattr(listener, "__name__"):
        return str(listener.__name__)
    return repr(listener)


class EventDispatcher:
    """
    集中型イベントディスパッチャ。
    イベントの購読と発行を管理します。
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[..., Any]]] = defaultdict(list)

    # ── Overloads for subscribe ─────────────────────────────────────────────
    @overload
    def subscribe(
        self,
        event_type: Literal["SETTINGS_CHANGED"],
        listener: Callable[[dict[str, Any]], Any],
    ) -> None: ...

    @overload
    def subscribe(
        self,
        event_type: Literal["HISTORY_UPDATED"],
        listener: Callable[[list[dict[str, Any]]], Any],
    ) -> None: ...

    @overload
    def subscribe(
        self, event_type: Literal["LANGUAGE_CHANGED"], listener: Callable[[str], Any]
    ) -> None: ...

    @overload
    def subscribe(
        self,
        event_type: Literal["HISTORY_ITEM_EDITED"],
        listener: Callable[[dict[str, Any]], Any],
    ) -> None: ...

    @overload
    def subscribe(
        self,
        event_type: Literal["REQUEST_UNDO_LAST_ACTION", "REQUEST_REDO_LAST_ACTION"],
        listener: Callable[[], Any],
    ) -> None: ...

    @overload
    def subscribe(self, event_type: str, listener: Callable[..., Any]) -> None: ...

    def subscribe(self, event_type: str, listener: Callable[..., Any]) -> None:
        """
        指定されたイベントタイプにリスナーを登録します。

        Args:
            event_type (str): 購読するイベントのタイプ。
            listener (Callable[..., Any]): イベント発生時に呼び出される関数。
        """
        self._listeners[event_type].append(listener)

    # ── Overloads for unsubscribe ───────────────────────────────────────────
    @overload
    def unsubscribe(
        self,
        event_type: Literal["SETTINGS_CHANGED"],
        listener: Callable[[dict[str, Any]], Any],
    ) -> None: ...

    @overload
    def unsubscribe(
        self,
        event_type: Literal["HISTORY_UPDATED"],
        listener: Callable[[list[dict[str, Any]]], Any],
    ) -> None: ...

    @overload
    def unsubscribe(
        self, event_type: Literal["LANGUAGE_CHANGED"], listener: Callable[[str], Any]
    ) -> None: ...

    @overload
    def unsubscribe(
        self,
        event_type: Literal["HISTORY_ITEM_EDITED"],
        listener: Callable[[dict[str, Any]], Any],
    ) -> None: ...

    @overload
    def unsubscribe(
        self,
        event_type: Literal["REQUEST_UNDO_LAST_ACTION", "REQUEST_REDO_LAST_ACTION"],
        listener: Callable[[], Any],
    ) -> None: ...

    @overload
    def unsubscribe(self, event_type: str, listener: Callable[..., Any]) -> None: ...

    def unsubscribe(self, event_type: str, listener: Callable[..., Any]) -> None:
        """
        指定されたイベントタイプからリスナーの登録を解除します。

        Args:
            event_type (str): 登録解除するイベントのタイプ。
            listener (Callable[..., Any]): 登録解除する関数。
        """
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)

    # ── Overloads for dispatch ──────────────────────────────────────────────
    @overload
    def dispatch(
        self, event_type: Literal["SETTINGS_CHANGED"], payload: dict[str, Any]
    ) -> None: ...

    @overload
    def dispatch(
        self,
        event_type: Literal["HISTORY_UPDATED"],
        history_items: list[dict[str, Any]],
    ) -> None: ...

    @overload
    def dispatch(self, event_type: Literal["LANGUAGE_CHANGED"], lang: str) -> None: ...

    @overload
    def dispatch(
        self, event_type: Literal["HISTORY_ITEM_EDITED"], item: dict[str, Any]
    ) -> None: ...

    @overload
    def dispatch(
        self,
        event_type: Literal["REQUEST_UNDO_LAST_ACTION", "REQUEST_REDO_LAST_ACTION"],
    ) -> None: ...

    @overload
    def dispatch(self, event_type: str, *args: Any, **kwargs: Any) -> None: ...

    def dispatch(self, event_type: str, *args: Any, **kwargs: Any) -> None:
        """
        指定されたイベントタイプを発行し、登録されているすべてのリスナーを呼び出します。

        Args:
            event_type (str): 発行するイベントのタイプ。
            *args: リスナーに渡す位置引数。
            **kwargs: リスナーに渡すキーワード引数。
        """
        for listener in self._listeners[event_type]:
            try:
                listener(*args, **kwargs)
            except Exception:
                listener_name = _get_listener_name(listener)
                log_and_show_error(
                    "エラー",
                    f"Error dispatching event {event_type} to listener {listener_name}: {traceback.format_exc()}",
                    exc_info=True,
                )
