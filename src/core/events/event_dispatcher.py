import logging
import traceback
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from src.utils.error_handler import log_and_show_error

logger = logging.getLogger(__name__)

class EventDispatcher:
    """
    集中型イベントディスパッチャ。
    イベントの購読と発行を管理します。
    """
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, listener: Callable[[Any], None]) -> None:
        """
        指定されたイベントタイプにリスナーを登録します。

        Args:
            event_type (str): 購読するイベントのタイプ。
            listener (Callable[[Any], None]): イベント発生時に呼び出される関数。
        """
        self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: str, listener: Callable[[Any], None]) -> None:
        """
        指定されたイベントタイプからリスナーの登録を解除します。

        Args:
            event_type (str): 登録解除するイベントのタイプ。
            listener (Callable[[Any], None]): 登録解除する関数。
        """
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)

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
                # エラーハンドリングを強化することも可能
                log_and_show_error("エラー",f"Error dispatching event {event_type} to listener {listener.__name__}: {traceback.format_exc()}", exc_info=True)
