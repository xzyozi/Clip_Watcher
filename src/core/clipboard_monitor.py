from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import logging
import os
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

from .event_dispatcher import EventDispatcher
from .notification_manager import NotificationManager
from src.db.database_manager import DatabaseManager
from src.db.dto import ClipboardHistoryDTO

if TYPE_CHECKING:
    pass  # For settings object


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ClipboardMonitor:
    def __init__(self, tk_root: tk.Tk, event_dispatcher: EventDispatcher, history_file_path: str, win32_available: bool, db_manager: DatabaseManager, history_limit: int = 50, excluded_apps: list[str] | None = None) -> None:
        self.tk_root = tk_root
        self.event_dispatcher = event_dispatcher
        self.win32_available = win32_available
        self.notification_manager = NotificationManager(None) # 設定はイベント経由で渡されます
        self.update_callback: Callable[[str, list[tuple[str, bool, float]]], None] | None = None
        self.error_callback: Callable[[str, str], None] | None = None
        self.last_clipboard_data: str = ""
        self._running: bool = False
        self.monitor_thread: threading.Thread | None = None
        self.history_file_path: str = history_file_path
        self.db_manager: DatabaseManager = db_manager
        
        self.history_limit: int = history_limit
        self.excluded_apps: list[str] = excluded_apps if excluded_apps is not None else []
        self.history: list[tuple[str, bool, float]] = self._load_history_from_db()
        self._dirty: bool = False
        self._auto_save_interval_ms: int = 5000

        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)

    def on_settings_changed(self, settings: dict[str, Any]) -> None:
        self.history_limit = settings.get("history_limit", 50)
        self.excluded_apps = settings.get("excluded_apps", [])
        self.notification_manager.update_settings(settings)
        if len(self.history) > self.history_limit:
            self.history = self.history[:self.history_limit]
            self._dirty = True
            self._trigger_gui_update()

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

    def set_gui_update_callback(self, callback: Callable[[str, list[tuple[str, bool, float]]], None]) -> None:
        self.update_callback = callback

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
        self.last_clipboard_data = text

        dto = ClipboardHistoryDTO(content=text, is_pinned=False)
        self.db_manager.history_dao.add_item(dto)
        self.db_manager.history_dao.cleanup_old(self.history_limit)
        
        self.history = self._load_history_from_db()

        # GUIの更新をトリガーして新しい履歴を表示します
        self._trigger_gui_update()

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

        dto = ClipboardHistoryDTO(content=clipboard_data, is_pinned=False)
        self.db_manager.history_dao.add_item(dto)
        self.db_manager.history_dao.cleanup_old(self.history_limit)

        self.history = self._load_history_from_db()

        # GUIの更新をトリガーして新しい履歴を表示します
        self._trigger_gui_update()

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
        db_id = int(item_id)
        import hashlib
        new_hash = hashlib.sha256(new_text.encode('utf-8')).hexdigest()
        
        success = self.db_manager.history_dao.update_content(db_id, new_text, new_hash)
        if success:
            if self.history and self.history[0][2] == item_id:
                self.last_clipboard_data = new_text
            self.history = self._load_history_from_db()
            self._trigger_gui_update()

    def _trigger_gui_update(self) -> None:
        if self.update_callback:
            self.tk_root.after(0, self.update_callback, self.last_clipboard_data, self.get_history())

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
        # The tuple is (content, is_pinned, db_id)
        pinned = [item for item in self.history if item[1]]
        unpinned = [item for item in self.history if not item[1]]
        return pinned + unpinned

    def clear_history(self) -> None:
        self.db_manager.history_dao.clear_all()
        self.history.clear()
        self.last_clipboard_data = ""
        self._trigger_gui_update()

    def delete_history_item_by_id(self, item_id: float) -> None:
        """Deletes a history item using its unique ID."""
        db_id = int(item_id)
        success = self.db_manager.history_dao.delete_item(db_id)
        if success:
            self.history = self._load_history_from_db()
            if not self.history:
                self.last_clipboard_data = ""
            self._trigger_gui_update()
            logging.info(f"ID {item_id} の履歴項目を削除しました。")
        else:
            logging.warning(f"ID {item_id} の履歴項目が見つかりませんでした。")

    def pin_item_by_id(self, item_id: float) -> None:
        """Pins an item using its unique ID."""
        db_id = int(item_id)
        success = self.db_manager.history_dao.pin_item(db_id, True)
        if success:
            self.history = self._load_history_from_db()
            self._trigger_gui_update()

    def unpin_item_by_id(self, item_id: float) -> None:
        """Unpins an item using its unique ID."""
        db_id = int(item_id)
        success = self.db_manager.history_dao.pin_item(db_id, False)
        if success:
            self.history = self._load_history_from_db()
            self._trigger_gui_update()

    def delete_all_unpinned_history(self) -> None:
        self.db_manager.history_dao.delete_unpinned()
        self.history = self._load_history_from_db()
        self._trigger_gui_update()
        logging.info("モニター: ピン留めされていないすべての履歴を削除しました。")

    def import_history(self, new_history_items: list[str]) -> None:
        for item_content in reversed(new_history_items):
            dto = ClipboardHistoryDTO(content=item_content, is_pinned=False)
            self.db_manager.history_dao.add_item(dto)
        self.db_manager.history_dao.cleanup_old(self.history_limit)
        self.history = self._load_history_from_db()
        self._trigger_gui_update()

    def get_filtered_history(self, query: str) -> list[tuple[str, bool, float]]:
        try:
            dtos = self.db_manager.history_dao.get_items(limit=self.history_limit, query=query)
            return [(dto.content, dto.is_pinned, float(dto.id or 0)) for dto in dtos]
        except Exception as e:
            logging.error(f"履歴のフィルタリング取得中にエラーが発生しました: %s", str(e), exc_info=True)
            return []

    def _load_history_from_db(self) -> list[tuple[str, bool, float]]:
        try:
            dtos = self.db_manager.history_dao.get_items(limit=self.history_limit)
            history = [(dto.content, dto.is_pinned, float(dto.id or 0)) for dto in dtos]
            if history:
                self.last_clipboard_data = history[0][0]
            return history
        except Exception as e:
            logging.error(f"データベースからの履歴読み込みに失敗しました: %s", str(e), exc_info=True)
            return []

    def _load_history_from_file(self) -> list[tuple[str, bool, float]]:
        # 後方互換性のために残していますが、移行後は空を返します
        return []

    def save_history_to_file(self) -> None:
        self._save_history_to_file()

    def _save_history_to_file(self) -> None:
        # DBに都度保存しているため、何もしません
        pass
