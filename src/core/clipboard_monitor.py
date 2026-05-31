from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import threading
import time
import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

try:
    import pywintypes
    import win32clipboard
except ImportError:
    # このモジュールはオプションであり、利用可能性は外部から注入されるフラグによって制御されます。
    pass

from src.db.database_manager import DatabaseManager
from src.services.notification_manager import NotificationManager

from .event_dispatcher import EventDispatcher

if TYPE_CHECKING:
    from src.services.history_service import HistoryService


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ClipboardMonitor:
    def __init__(self, tk_root: tk.Tk, event_dispatcher: EventDispatcher, history_file_path: str, win32_available: bool, db_manager: DatabaseManager, history_service: HistoryService, history_limit: int = 50, excluded_apps: list[str] | None = None) -> None:
        self.tk_root = tk_root
        self.event_dispatcher = event_dispatcher
        self.win32_available = win32_available
        self.notification_manager = NotificationManager(None) # 設定はイベント経由で渡されます
        self.error_callback: Callable[[str, str], None] | None = None
        self._running: bool = False
        self.monitor_thread: threading.Thread | None = None
        self.history_file_path: str = history_file_path
        self.db_manager: DatabaseManager = db_manager
        self.history_service = history_service

        self.history_limit: int = history_limit
        self.excluded_apps: list[str] = excluded_apps if excluded_apps is not None else []
        self._dirty: bool = False
        self._auto_save_interval_ms: int = 5000

        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)

    @property
    def history(self) -> list[tuple[str, bool, float]]:
        return self.history_service.history

    @history.setter
    def history(self, value: list[tuple[str, bool, float]]) -> None:
        self.history_service.history = value

    @property
    def last_clipboard_data(self) -> str:
        return self.history_service.last_clipboard_data

    @last_clipboard_data.setter
    def last_clipboard_data(self, value: str) -> None:
        self.history_service.last_clipboard_data = value

    def on_settings_changed(self, settings: dict[str, Any]) -> None:
        self.history_limit = settings.get("history_limit", 50)
        self.excluded_apps = settings.get("excluded_apps", [])
        self.notification_manager.update_settings(settings)

    def set_error_callback(self, callback: Callable[[str, str], None]) -> None:
        self.error_callback = callback

    def get_active_process_name(self) -> str | None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        process_handle = kernel32.OpenProcess(0x0410, False, pid.value)
        if not process_handle:
            return None

        exe_name = (ctypes.c_char * 260)()
        psapi.GetModuleBaseNameA(process_handle, None, exe_name, 260)
        kernel32.CloseHandle(process_handle)

        return exe_name.value.decode(errors="ignore")

    def update_clipboard(self, text: str) -> None:
        """プログラムでシステムクリップボードを更新し、新しいエントリとして扱います。"""
        if not text:
            return

        # テキストが最新の履歴アイテムと同一である場合、重複したエントリの追加を避けます。
        if self.history and text == self.history[0][0]:
            return

        try:
            # 最初にシステムクリップボードを更新します
            self.tk_root.clipboard_clear()
            self.tk_root.clipboard_append(text)
            self.tk_root.update()
        except Exception as e:
            logging.error(f"プログラムによるクリップボードの更新に失敗しました: {e}", exc_info=True)
            return # クリップボードの更新に失敗した場合、履歴は変更しません

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
                logging.error("クリップボード監視ループで予期せぬエラーが発生しました。", exc_info=True)
                time.sleep(5)

    def _decode_clipboard_data(self, data: Any) -> str:
        if isinstance(data, bytes):
            encodings = ['utf-8', 'shift-jis', 'cp932', 'euc-jp', 'latin1']
            for encoding in encodings:
                try:
                    return data.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return data.decode('utf-8', errors='ignore')
        elif isinstance(data, str):
            try:
                return data.encode('utf-8', errors='surrogateescape').decode('utf-8', errors='ignore')
            except Exception:
                return data
        return str(data)

    def _get_clipboard_content(self) -> str | None:
        """
        tkinterを使用してクリップボードのコンテンツを取得し、失敗した場合はwin32clipboardにフォールバックします。
        コンテンツを文字列として返すか、失敗した場合やコンテンツがテキストでない場合はNoneを返します。
        """
        # 1. 最初にtkinterを試します
        try:
            return self.tk_root.clipboard_get()
        except (tk.TclError, UnicodeDecodeError) as e:
            logging.warning(f"tkinterのclipboard_getに失敗しました ({e})。win32clipboardにフォールバックします。")

        # 2. win32clipboardが利用可能な場合にフォールバックします
        if not self.win32_available:
            logging.warning("win32clipboardが利用できないため、フォールバックできません。")
            return None

        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT): # type: ignore
                return cast(str, win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT))
            elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT): # type: ignore
                data = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                return self._decode_clipboard_data(data)
            return "" # 処理できないテキスト形式です
        except pywintypes.error as e:
            if e.winerror == 5: # アクセスが拒否されました
                logging.warning("win32clipboardがクリップボードを開けませんでした（アクセス拒否）。使用中の可能性があります。")
            else:
                logging.error(f"win32clipboardフォールバックが予期せぬエラーで失敗しました: {e}", exc_info=True)
            return None # 失敗したことを示します
        except Exception as e:
            logging.error(f"win32clipboardフォールバックが一般的なエラーで失敗しました: {e}", exc_info=True)
            return None # 失敗したことを示します
        finally:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass # すでに閉じられているか、開けませんでした。

    def _update_history_with_new_entry(self, clipboard_data: str) -> None:
        """新しいクリップボードエントリで履歴を更新します。"""
        self.last_clipboard_data = clipboard_data
        active_process = self.get_active_process_name()
        logging.info(f"クリップボードの更新を検出 - プロセス: {active_process}")

        if active_process in self.excluded_apps:
            logging.info(f"除外アプリからのコピーのため無視: {active_process}")
            return

        self.history_service.add_history_item(clipboard_data)

    def _check_clipboard(self) -> None:
        try:
            # 1. 堅牢な方法でクリップボードのコンテンツを取得します
            raw_content = self._get_clipboard_content()
            if raw_content is None:
                return # コンテンツの取得に失敗したか、テキストではありません

            # 2. 正規化と検証
            try:
                clipboard_data = self._decode_clipboard_data(raw_content)
            except Exception:
                clipboard_data = str(raw_content)

            if not clipboard_data:
                return

            if len(clipboard_data) > 1024 * 1024:
                # logging.warning("クリップボードのコンテンツが大きすぎるため、スキップします。")
                return

            # 3. 新しい場合、処理します
            if clipboard_data != self.last_clipboard_data:
                self._update_history_with_new_entry(clipboard_data)

        except Exception:
            logging.error("クリップボードのチェック中に予期せぬエラーが発生しました。", exc_info=True)

    def update_history_item_by_id(self, item_id: float, new_text: str) -> None:
        """Finds a history item by its ID and updates its content."""
        self.history_service.update_history_item_by_id(item_id, new_text)



    def start(self) -> None:
        if not self._running:
            self._running = True
            self.monitor_thread = threading.Thread(target=self._monitor_clipboard, daemon=True) # type: ignore
            self.monitor_thread.start() # type: ignore
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

    def get_history(self) -> list[tuple[str, bool, float]]:
        return self.history_service.get_history()

    def clear_history(self) -> None:
        self.history_service.clear_history()

    def delete_history_item_by_id(self, item_id: float) -> None:
        """Deletes a history item using its unique ID."""
        self.history_service.delete_history_item_by_id(item_id)

    def pin_item_by_id(self, item_id: float) -> None:
        """Pins an item using its unique ID."""
        self.history_service.pin_item_by_id(item_id)

    def unpin_item_by_id(self, item_id: float) -> None:
        """Unpins an item using its unique ID."""
        self.history_service.unpin_item_by_id(item_id)

    def delete_all_unpinned_history(self) -> None:
        self.history_service.delete_all_unpinned_history()

    def import_history(self, new_history_items: list[str]) -> None:
        self.history_service.import_history(new_history_items)

    def get_filtered_history(self, query: str) -> list[tuple[str, bool, float]]:
        return self.history_service.get_filtered_history(query)

    def _load_history_from_db(self) -> list[tuple[str, bool, float]]:
        return self.history_service.load_history()

    def _load_history_from_file(self) -> list[tuple[str, bool, float]]:
        # 後方互換性のために残していますが、移行後は空を返します
        return []

    def save_history_to_file(self) -> None:
        self._save_history_to_file()

    def _save_history_to_file(self) -> None:
        # DBに都度保存しているため、何もしません
        pass
