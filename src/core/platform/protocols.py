"""src/core/platform/protocols.py

OSプラットフォーム依存機能（プロセス取得、多重起動防止、効果音、ホットキー、キーストローク送信）
を抽象化するプロトコル（境界インターフェース）定義。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProcessInspector(Protocol):
    """現在アクティブなウィンドウ・プロセスの情報を検査するインターフェース。"""

    def get_active_process_name(self) -> str | None:
        """フォアグラウンドウィンドウの実行可能ファイル名（小文字等）を返す。

        取得に失敗した場合や非対応環境の場合は None を返す。
        """
        ...


@runtime_checkable
class SingleInstanceController(Protocol):
    """アプリケーションの多重起動（単一インスタンス排他制御）を司るインターフェース。"""

    def acquire(self) -> bool:
        """排他ロックを取得する。

        すでに他のインスタンスが起動している場合は False を返す。
        正常にロックを取得でき、自身がプライマリインスタンスである場合は True を返す。
        """
        ...

    def release(self) -> None:
        """保持している排他ロックを解放する。"""
        ...


@runtime_checkable
class SoundPlayer(Protocol):
    """通知音・ビープ音の再生を司るインターフェース。"""

    def play_notification_beep(
        self, frequency: int = 1000, duration_ms: int = 200
    ) -> bool:
        """指定された周波数とミリ秒で通知ビープ音を再生する。

        再生に成功した場合は True、失敗または非対応環境の場合は False を返す。
        """
        ...


@runtime_checkable
class PasteSender(Protocol):
    """アクティブウィンドウへの貼り付けキーストローク送信と修飾キー状態判定を司るインターフェース。"""

    def are_modifiers_released(self) -> bool:
        """物理的な修飾キー（Ctrl, Alt, Shift等）がすべて解放されているか判定する。"""
        ...

    def paste_active_window(self) -> bool:
        """現在アクティブなウィンドウへ貼り付け操作（Ctrl+Vなど）を送信する。

        送信に成功した場合は True、失敗した場合は False を返す。
        """
        ...


@runtime_checkable
class HotkeyListener(Protocol):
    """グローバルホットキーの登録と監視イベントループを司るインターフェース。"""

    def start(self, modifiers: int, vk_code: int) -> bool:
        """単一のグローバルホットキーを登録して監視を開始する。"""
        ...

    def start_many(self, registrations: Iterable[Any]) -> bool:
        """複数のグローバルホットキー登録集合を受け取り、監視を開始する。"""
        ...

    def stop(self) -> None:
        """ホットキー監視スレッドを安全に停止し、登録をすべて解除する。"""
        ...
