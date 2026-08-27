from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any

from src.core.config.defaults import DEFAULT_USER_SETTINGS
from src.db.dto import ClipboardHistoryDTO

if TYPE_CHECKING:
    from src.core.events.event_dispatcher import EventDispatcher
    from src.db.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

# history_limit のデフォルト値は defaults.DEFAULT_USER_SETTINGS を単一の参照元とする。
_default_history_limit = DEFAULT_USER_SETTINGS["history_limit"]
_DEFAULT_HISTORY_LIMIT: int = (
    _default_history_limit if isinstance(_default_history_limit, int) else 50
)


class HistoryService:
    """履歴データおよびその永続化・状態操作を管理するサービス（単一責任原則に基づく）"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        event_dispatcher: EventDispatcher,
        history_limit: int = _DEFAULT_HISTORY_LIMIT,
    ) -> None:
        self.db_manager = db_manager
        self.event_dispatcher = event_dispatcher
        self.history_limit = history_limit
        self.last_clipboard_data: str = ""
        self.history: list[tuple[str, bool, float]] = []

        # データベースから初期履歴を読み込み
        self.load_history()

        # 設定変更イベントの購読
        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)

    def on_settings_changed(self, settings: dict[str, Any]) -> None:
        """設定変更イベント時のハンドラー。履歴表示制限件数を更新します。

        起動シーケンス上、HistoryService はデフォルト値（history_limit=50）で
        初期化され、その後に settings.json が読み込まれて SETTINGS_CHANGED が
        発火する（ApplicationBuilder.build() 末尾の load_and_notify() 呼び出し）。
        そのため、設定ファイルの history_limit がデフォルトより大きい場合、
        メモリ上の self.history は既に古い（小さい）上限で読み込まれた件数しか
        保持していない。上限が増えた場合は DB から再読み込みし、上限が減った
        場合は既存のトリム処理で対応する。
        """
        new_limit = settings.get("history_limit", _DEFAULT_HISTORY_LIMIT)
        limit_increased = new_limit > self.history_limit
        self.history_limit = new_limit

        if limit_increased:
            # 上限が増えた場合、現在メモリ上の件数が新しい上限に達しているかに
            # 関わらず、DBには上限を超えて残っている可能性があるため再読込する。
            self.load_history()
            self._notify_updated()
        elif len(self.history) > self.history_limit:
            self.history = self.history[: self.history_limit]
            self._notify_updated()

    def load_history(self) -> list[tuple[str, bool, float]]:
        """データベースから最新の履歴データを取得し、内部状態を更新します。"""
        try:
            dtos = self.db_manager.history_dao.get_items(limit=self.history_limit)
            self.history = [
                (dto.content, dto.is_pinned, float(dto.id or 0)) for dto in dtos
            ]
            if self.history:
                # 表示順序（ピン留め優先）ではなく、実際に最後にクリップボードへ
                # コピーされた内容（created_at が最新の項目）を last_clipboard_data
                # に設定する。これを誤ると、ピン留め項目がある状態でクリップボード
                # の変化判定が常に真になり、重複挿入ログが無限に出続けるバグになる。
                last_added = self.db_manager.history_dao.get_last_added_content()
                self.last_clipboard_data = (
                    last_added if last_added is not None else self.history[0][0]
                )
            else:
                self.last_clipboard_data = ""
            return self.history
        except Exception as e:
            logger.error(
                f"データベースからの履歴読み込みに失敗しました: {e}", exc_info=True
            )
            return []

    def get_history(self) -> list[tuple[str, bool, float]]:
        """ピン留めされた項目が先頭に来るように並び替えた現在の履歴リストを取得します。"""
        pinned = [item for item in self.history if item[1]]
        unpinned = [item for item in self.history if not item[1]]
        return pinned + unpinned

    def add_history_item(self, text: str) -> None:
        """新しいクリップボードエントリを履歴に追加します。"""
        if not text:
            return

        # 重複チェック。
        # last_clipboard_data は呼び出し元（ClipboardMonitor._update_history_with_new_entry）
        # がこのメソッド呼び出し前に先行更新する場合があるため、判定には使用しない。
        # 代わりに self.history 内で id（挿入順）が最大の項目を「実際に最後に
        # 追加/更新された項目」とみなして比較する。これはピン留めによる表示順序
        # （is_pinned優先ソート）の影響を受けない。
        if self.history:
            last_touched = max(self.history, key=lambda item: item[2])
            if text == last_touched[0]:
                return

        try:
            dto = ClipboardHistoryDTO(content=text, is_pinned=False)
            self.db_manager.history_dao.add_item(dto)
            self.db_manager.history_dao.cleanup_old(self.history_limit)

            self.last_clipboard_data = text
            self.load_history()
            self._notify_updated()
        except Exception as e:
            logger.error(f"履歴項目の追加に失敗しました: {e}", exc_info=True)

    def update_history_item_by_id(self, item_id: float, new_text: str) -> None:
        """指定されたIDの履歴項目のコンテンツを更新します。"""
        db_id = int(item_id)
        new_hash = hashlib.sha256(new_text.encode("utf-8")).hexdigest()

        try:
            success = self.db_manager.history_dao.update_content(
                db_id, new_text, new_hash
            )
            if success:
                if self.history and self.history[0][2] == item_id:
                    self.last_clipboard_data = new_text
                self.load_history()
                self._notify_updated()
        except Exception as e:
            logger.error(
                f"履歴項目の更新に失敗しました (ID: {item_id}): {e}", exc_info=True
            )

    def delete_history_item_by_id(self, item_id: float) -> None:
        """指定されたIDの履歴項目を削除します。"""
        db_id = int(item_id)
        try:
            success = self.db_manager.history_dao.delete_item(db_id)
            if success:
                self.load_history()
                if not self.history:
                    self.last_clipboard_data = ""
                self._notify_updated()
                logger.info(f"ID {item_id} の履歴項目を削除しました。")
            else:
                logger.warning(f"ID {item_id} の履歴項目が見つかりませんでした。")
        except Exception as e:
            logger.error(
                f"履歴項目の削除に失敗しました (ID: {item_id}): {e}", exc_info=True
            )

    def pin_item_by_id(self, item_id: float) -> None:
        """指定されたIDの履歴項目をピン留めします。"""
        db_id = int(item_id)
        try:
            success = self.db_manager.history_dao.pin_item(db_id, True)
            if success:
                self.load_history()
                self._notify_updated()
        except Exception as e:
            logger.error(
                f"履歴項目のピン留めに失敗しました (ID: {item_id}): {e}", exc_info=True
            )

    def unpin_item_by_id(self, item_id: float) -> None:
        """指定されたIDの履歴項目のピン留めを解除します。"""
        db_id = int(item_id)
        try:
            success = self.db_manager.history_dao.pin_item(db_id, False)
            if success:
                self.load_history()
                self._notify_updated()
        except Exception as e:
            logger.error(
                f"履歴項目のピン留め解除に失敗しました (ID: {item_id}): {e}",
                exc_info=True,
            )

    def clear_history(self) -> None:
        """すべての履歴データを削除します。"""
        try:
            self.db_manager.history_dao.clear_all()
            self.history.clear()
            self.last_clipboard_data = ""
            self._notify_updated()
            logger.info("すべての履歴項目を削除しました。")
        except Exception as e:
            logger.error(f"履歴全体の削除に失敗しました: {e}", exc_info=True)

    def delete_all_unpinned_history(self) -> None:
        """ピン留めされていないすべての履歴データを削除します。"""
        try:
            self.db_manager.history_dao.delete_unpinned()
            self.load_history()
            self._notify_updated()
            logger.info("ピン留めされていないすべての履歴を削除しました。")
        except Exception as e:
            logger.error(
                f"ピン留めされていない履歴の削除に失敗しました: {e}", exc_info=True
            )

    def import_history(self, new_history_items: list[str]) -> None:
        """外部からテキスト配列を履歴項目として一括インポートします。"""
        import time

        try:
            base_time = time.time()
            for i, item_content in enumerate(reversed(new_history_items)):
                # 基準時間を固定し、そこからデクリメントすることで、DBの書き込み遅延に影響されず正しい順序を保ちます
                dto = ClipboardHistoryDTO(
                    content=item_content,
                    is_pinned=False,
                    created_at=base_time - i * 0.01,
                )
                self.db_manager.history_dao.add_item(dto)
            self.db_manager.history_dao.cleanup_old(self.history_limit)
            self.load_history()
            self._notify_updated()
        except Exception as e:
            logger.error(f"履歴の一括インポートに失敗しました: {e}", exc_info=True)

    def get_filtered_history(self, query: str) -> list[tuple[str, bool, float]]:
        """検索クエリに合致する履歴項目を取得します。"""
        try:
            dtos = self.db_manager.history_dao.get_items(
                limit=self.history_limit, query=query
            )
            return [(dto.content, dto.is_pinned, float(dto.id or 0)) for dto in dtos]
        except Exception as e:
            logger.error(
                f"履歴のフィルタリング取得中にエラーが発生しました: {e}", exc_info=True
            )
            return []

    def _notify_updated(self) -> None:
        """履歴の状態が更新されたことをイベント経由で通知します。"""
        self.event_dispatcher.dispatch(
            "HISTORY_UPDATED",
            {"last_content": self.last_clipboard_data, "history": self.get_history()},
        )
