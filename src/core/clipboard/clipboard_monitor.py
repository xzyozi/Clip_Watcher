from __future__ import annotations

import logging
import threading
import time
import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from src.core.config.defaults import DEFAULT_USER_SETTINGS
from src.core.events.event_dispatcher import EventDispatcher
from src.core.platform.errors import UnsupportedFeatureError
from src.core.platform.services import PlatformServices
from src.db.database_manager import DatabaseManager
from src.utils.clipboard_decode import decode_clipboard_data

# history_limit のデフォルト値は defaults.DEFAULT_USER_SETTINGS を単一の参照元とする。
_default_history_limit = DEFAULT_USER_SETTINGS["history_limit"]
_DEFAULT_HISTORY_LIMIT: int = (
    _default_history_limit if isinstance(_default_history_limit, int) else 50
)

if TYPE_CHECKING:
    from src.services.history_service import HistoryService


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ClipboardMonitor:
    def __init__(
        self,
        tk_root: tk.Tk,
        event_dispatcher: EventDispatcher,
        history_file_path: str,
        db_manager: DatabaseManager,
        history_service: HistoryService,
        platform_services: PlatformServices,
        history_limit: int = _DEFAULT_HISTORY_LIMIT,
        excluded_apps: list[str] | None = None,
    ) -> None:
        self.tk_root = tk_root
        self.event_dispatcher = event_dispatcher
        self.platform_services = platform_services
        self._process_inspector_support_reported: bool = False
        self._clipboard_reader_support_reported: bool = False
        self.error_callback: Callable[[str, str], None] | None = None
        self._running: bool = False
        self.monitor_thread: threading.Thread | None = None
        self.history_file_path: str = history_file_path
        self.db_manager: DatabaseManager = db_manager
        self.history_service = history_service

        self.history_limit: int = history_limit
        self.excluded_apps: list[str] = (
            excluded_apps if excluded_apps is not None else []
        )
        self._dirty: bool = False
        self._auto_save_interval_ms: int = 5000

        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)

    def on_settings_changed(self, settings: dict[str, Any]) -> None:
        self.history_limit = settings.get("history_limit", _DEFAULT_HISTORY_LIMIT)
        self.excluded_apps = settings.get("excluded_apps", [])

    def set_error_callback(self, callback: Callable[[str, str], None]) -> None:
        self.error_callback = callback

    def get_active_process_name(self) -> str | None:
        """アクティブなプロセス名を返す。非対応環境では None（除外判定は行われない）。

        非対応であることは start() で一度だけ警告する。ここでは繰り返しログを出さない。
        """
        try:
            inspector = self.platform_services.process_inspector()
        except UnsupportedFeatureError:
            return None
        return inspector.get_active_process_name()

    def _report_process_inspector_support(self) -> None:
        """ProcessInspector が非対応の場合に、起動時に一度だけ明示的に警告する。

        除外アプリ判定ができない状態で履歴保存を継続するため、excluded_apps が
        設定されている（設定があるのに効かない）場合は ERROR に格上げする。
        """
        if self._process_inspector_support_reported:
            return
        self._process_inspector_support_reported = True

        try:
            self.platform_services.process_inspector()
        except UnsupportedFeatureError as e:
            if self.excluded_apps:
                logging.error(
                    "process_inspector が非対応のため、excluded_apps の設定は無視されます。"
                    "除外対象のアプリからのコピーも履歴に保存されます: %s",
                    e,
                )
            else:
                logging.warning(
                    "process_inspector が非対応のため、除外アプリの判定は行われません: %s",
                    e,
                )

    def update_clipboard(self, text: str) -> None:
        """プログラムでシステムクリップボードを更新し、新しいエントリとして扱います。"""
        if not text:
            return

        # テキストが直近のクリップボード内容と同一である場合、重複したエントリの
        # 追加を避けます。ピン留め項目による表示順序（is_pinned優先ソート）に
        # 影響されないよう、id（挿入順）が最大の項目と比較する。
        history = self.history_service.history
        if history:
            last_touched = max(history, key=lambda item: item[2])
            if text == last_touched[0]:
                return

        try:
            # 最初にシステムクリップボードを更新します
            self.tk_root.clipboard_clear()
            self.tk_root.clipboard_append(text)
            self.tk_root.update()
        except Exception as e:
            logging.error(
                f"プログラムによるクリップボードの更新に失敗しました: {e}",
                exc_info=True,
            )
            return  # クリップボードの更新に失敗した場合、履歴は変更しません

        # _check_clipboardのロジックを模倣して、履歴を直接更新します
        self.history_service.add_history_item(text)

    def _monitor_clipboard(self) -> None:
        logging.info("クリップボード監視を開始します")
        while self._running:
            try:
                self.tk_root.after(0, self._check_clipboard)
                time.sleep(0.5)
            except RuntimeError as e:
                logging.warning(f"Tkinterランタイムエラー: {e}")
                time.sleep(1)
            except Exception:
                logging.error(
                    "クリップボード監視ループで予期せぬエラーが発生しました。",
                    exc_info=True,
                )
                time.sleep(5)

    def _decode_clipboard_data(self, data: Any) -> str:
        return decode_clipboard_data(data)

    def _get_clipboard_content(self) -> str | None:
        """
        tkinterを使用してクリップボードのコンテンツを取得し、失敗した場合は
        PlatformServices の ClipboardReader にフォールバックします。
        コンテンツを文字列として返すか、失敗した場合やコンテンツがテキストでない場合はNoneを返します。
        """
        # 1. 最初にtkinterを試します
        try:
            return self.tk_root.clipboard_get()
        except (tk.TclError, UnicodeDecodeError) as e:
            logging.warning(
                f"tkinterのclipboard_getに失敗しました ({e})。ClipboardReaderにフォールバックします。"
            )

        # 2. OS 固有の ClipboardReader が利用可能な場合にフォールバックします
        try:
            reader = self.platform_services.clipboard_reader()
        except UnsupportedFeatureError as e:
            # 非対応であることは一度だけ警告し、ポーリングごとのログ氾濫を避ける
            if not self._clipboard_reader_support_reported:
                self._clipboard_reader_support_reported = True
                logging.warning(
                    "clipboard_reader が非対応のため、tkinter 失敗時のフォールバックはできません: %s",
                    e,
                )
            return None

        return reader.read_text()

    def _update_history_with_new_entry(self, clipboard_data: str) -> None:
        """新しいクリップボードエントリで履歴を更新します。"""
        self.history_service.last_clipboard_data = clipboard_data
        active_process = self.get_active_process_name()
        logging.info(f"クリップボードの更新を検出 - プロセス: {active_process}")

        # Windows の GetModuleBaseNameA は実行ファイルの実体ケース（例: KeePass.exe）を
        # 返す一方、excluded_apps には小文字（keepass.exe）で登録されることがある。
        # Windows のファイルシステムは大文字小文字を区別しないため、比較時のみ両側を
        # 小文字化して確実に除外する（ログ表示は視認性のため実体ケースを維持する）。
        if active_process is not None and active_process.lower() in {
            app.lower() for app in self.excluded_apps
        }:
            logging.info(f"除外アプリからのコピーのため無視: {active_process}")
            return

        self.history_service.add_history_item(clipboard_data)

    def get_current_clipboard_text(self) -> str | None:
        """現在のシステムクリップボードからテキストを取得して検証・正規化した文字列を返す。

        テキストが存在しない場合、取得に失敗した場合、空文字、またはサイズ超過
        （1MB超）の場合は None を返します。
        """
        raw_content = self._get_clipboard_content()
        if raw_content is None:
            return None

        try:
            clipboard_data = self._decode_clipboard_data(raw_content)
        except Exception:
            clipboard_data = str(raw_content)

        if not clipboard_data:
            return None

        if len(clipboard_data) > 1024 * 1024:
            return None

        return clipboard_data

    def sync_initial_clipboard(self) -> str | None:
        """起動シーケンスにおいて現在のOSクリップボード内容を即座に取得・同期する。

        取得できたテキストがDBの最新履歴（last_clipboard_data）と異なる場合は
        新しいエントリとして履歴に登録し、画面・内部状態を更新する。
        同一の場合は重複登録を避けてそのまま返す。
        取得したテキスト（またはNone）を返す。
        """
        try:
            clipboard_data = self.get_current_clipboard_text()
            if clipboard_data is None:
                return None

            if clipboard_data != self.history_service.last_clipboard_data:
                self._update_history_with_new_entry(clipboard_data)

            return clipboard_data
        except Exception:
            logging.error(
                "起動時のクリップボード同期中に予期せぬエラーが発生しました。",
                exc_info=True,
            )
            return None

    def _check_clipboard(self) -> None:
        try:
            clipboard_data = self.get_current_clipboard_text()
            if clipboard_data is None:
                return

            if clipboard_data != self.history_service.last_clipboard_data:
                self._update_history_with_new_entry(clipboard_data)

        except Exception:
            logging.error(
                "クリップボードのチェック中に予期せぬエラーが発生しました。",
                exc_info=True,
            )

    def start(self) -> None:
        if not self._running:
            self._report_process_inspector_support()
            self._running = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_clipboard, daemon=True
            )  # type: ignore
            self.monitor_thread.start()  # type: ignore
            self._schedule_auto_save_check()

    def _schedule_auto_save_check(self) -> None:
        if self._running:
            self.tk_root.after(self._auto_save_interval_ms, self._auto_save_check)

    def _auto_save_check(self) -> None:
        if not self._running:
            return
        # DBに都度保存しているため、ここでは何もしません
        self._schedule_auto_save_check()

    def stop(self) -> None:
        self._running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)

    def save_history_to_file(self) -> None:
        self._save_history_to_file()

    def _save_history_to_file(self) -> None:
        # DBに都度保存しているため、何もしません
        pass
