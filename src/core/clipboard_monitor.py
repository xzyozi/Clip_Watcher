import time
import threading
import tkinter as tk
import json
import os
import ctypes
import ctypes.wintypes
import logging

try:
    import win32clipboard
    import pywintypes
except ImportError:
    # このモジュールはオプションであり、利用可能性は外部から注入されるフラグによって制御されます。
    pass

from .notification_manager import NotificationManager
from .event_dispatcher import EventDispatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ClipboardMonitor:
    def __init__(self, tk_root, event_dispatcher: EventDispatcher, history_file_path, win32_available: bool, history_limit=50, excluded_apps=None):
        self.tk_root = tk_root
        self.event_dispatcher = event_dispatcher
        self.win32_available = win32_available
        self.notification_manager = NotificationManager(None) # 設定はイベント経由で渡されます
        self.update_callback = None
        self.error_callback = None
        self.last_clipboard_data = ""
        self._running = False
        self.monitor_thread = None
        self.history_file_path = history_file_path
        self.history = self._load_history_from_file()
        self.history_limit = history_limit
        self.excluded_apps = excluded_apps if excluded_apps is not None else []

        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)

    def on_settings_changed(self, settings):
        self.history_limit = settings.get("history_limit", 50)
        self.excluded_apps = settings.get("excluded_apps", [])
        self.notification_manager.update_settings(settings)
        if len(self.history) > self.history_limit:
            self.history = self.history[:self.history_limit]
            self._trigger_gui_update()

    def set_error_callback(self, callback):
        self.error_callback = callback

    def get_active_process_name(self):
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

    def set_gui_update_callback(self, callback):
        self.update_callback = callback

    def update_clipboard(self, text: str):
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
        
        existing_item_index = -1
        for i, (content, is_pinned) in enumerate(self.history):
            if content == text:
                existing_item_index = i
                break

        if existing_item_index != -1:
            # 項目が存在する場合、一番上に移動します
            content_to_move, is_pinned_status = self.history.pop(existing_item_index)
            self.history.insert(0, (content_to_move, is_pinned_status))
        else:
            # 新しい項目の場合、一番上に追加します
            self.history.insert(0, (text, False))
            # 制限を超えた場合、履歴を整理します
            if len(self.history) > self.history_limit:
                # 削除するために最後のピン留めされていない項目を見つけます
                unpinned_indices = [i for i, (_, is_pinned) in enumerate(self.history) if not is_pinned]
                if unpinned_indices:
                    del self.history[unpinned_indices[-1]]
        
        # GUIの更新をトリガーして新しい履歴を表示します
        self._trigger_gui_update()

    def _monitor_clipboard(self):
        logging.info("クリップボード監視を開始します")
        while self._running:
            try:
                self.tk_root.after(0, self._check_clipboard)
                time.sleep(0.5)
            except RuntimeError as e:
                logging.warning(f"Tkinterランタイムエラー: {e}")
                time.sleep(1)
            except Exception as e:
                logging.error("クリップボード監視ループで予期せぬエラーが発生しました。", exc_info=True)
                time.sleep(5)

    def _decode_clipboard_data(self, data):
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

    def _get_clipboard_content(self):
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
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT):
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

    def _update_history_with_new_entry(self, clipboard_data):
        """新しいクリップボードエントリで履歴を更新します。"""
        self.last_clipboard_data = clipboard_data
        active_process = self.get_active_process_name()
        logging.info(f"クリップボードの更新を検出 - プロセス: {active_process}")
        
        if active_process in self.excluded_apps:
            logging.info(f"除外アプリからのコピーのため無視: {active_process}")
            return
        
        # 既存の項目を一番上に移動するか、新しい項目を追加します
        existing_item_index = -1
        for i, (content, is_pinned) in enumerate(self.history):
            if content == clipboard_data:
                existing_item_index = i
                break

        if existing_item_index != -1:
            content_to_move, is_pinned_status = self.history.pop(existing_item_index)
            self.history.insert(0, (content_to_move, is_pinned_status))
        else:
            self.history.insert(0, (clipboard_data, False))
            # 制限を超えた場合、履歴を整理します
            if len(self.history) > self.history_limit:
                unpinned = [i for i, (_, is_pinned) in enumerate(self.history) if not is_pinned]
                if unpinned:
                    del self.history[unpinned[-1]]

        self.notification_manager.play_notification_sound()
        self._trigger_gui_update()

    def _check_clipboard(self):
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

        except Exception as e:
            logging.error("クリップボードのチェック中に予期せぬエラーが発生しました。", exc_info=True)

    def update_history_item(self, old_text: str, new_text: str):
        """コンテンツによって履歴項目を見つけて更新します。"""
        for i, (content, is_pinned) in enumerate(self.history):
            if content == old_text:
                self.history[i] = (new_text, is_pinned)
                # 更新された項目が最新のものであった場合、last_clipboard_dataも更新します
                if self.last_clipboard_data == old_text:
                    self.last_clipboard_data = new_text
                self._trigger_gui_update()
                return

    def _trigger_gui_update(self):
        if self.update_callback:
            self.tk_root.after(0, self.update_callback, self.last_clipboard_data, self.get_history())

    def start(self):
        if not self._running:
            self._running = True
            self.monitor_thread = threading.Thread(target=self._monitor_clipboard, daemon=True)
            self.monitor_thread.start()

    def stop(self):
        self._running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)

    def get_history(self):
        pinned = [item for item in self.history if item[1]]
        unpinned = [item for item in self.history if not item[1]]
        return pinned + unpinned

    def clear_history(self):
        self.history.clear()
        self.last_clipboard_data = ""
        self._trigger_gui_update()

    def delete_history_item(self, index):
        current_display_history = self.get_history()
        if 0 <= index < len(current_display_history):
            item_to_delete = current_display_history[index]
            for i, hist_item in enumerate(self.history):
                if hist_item == item_to_delete:
                    del self.history[i]
                    break
            
            if not self.history:
                self.last_clipboard_data = ""
            self._trigger_gui_update()

    def pin_item(self, item_to_pin):
        for i, (content, is_pinned) in enumerate(self.history):
            if (content, is_pinned) == item_to_pin:
                self.history[i] = (content, True)
                self._trigger_gui_update()
                return

    def unpin_item(self, item_to_unpin):
        for i, (content, is_pinned) in enumerate(self.history):
            if (content, is_pinned) == item_to_unpin:
                self.history[i] = (content, False)
                self._trigger_gui_update()
                return

    def delete_all_unpinned_history(self):
        self.history = [item for item in self.history if item[1]]
        self._trigger_gui_update()
        logging.info("モニター: ピン留めされていないすべての履歴を削除しました。")

    def import_history(self, new_history_items):
        for item_content in reversed(new_history_items):
            new_item = (item_content, False)
            existing_item_index = -1
            for i, (content, is_pinned) in enumerate(self.history):
                if content == item_content:
                    existing_item_index = i
                    break
            
            if existing_item_index != -1:
                content_to_move, is_pinned_status = self.history.pop(existing_item_index)
                self.history.insert(0, (content_to_move, is_pinned_status))
            else:
                self.history.insert(0, new_item)
                if len(self.history) > self.history_limit:
                    self.history.pop()
        self._trigger_gui_update()

    def get_filtered_history(self, query):
        filtered_raw = [item for item in self.history if query.lower() in item[0].lower()]
        
        pinned = [item for item in filtered_raw if item[1]]
        unpinned = [item for item in filtered_raw if not item[1]]
        return pinned + unpinned

    def _load_history_from_file(self):
        if os.path.exists(self.history_file_path):
            try:
                with open(self.history_file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    return [(item[0], item[1]) for item in loaded_data if isinstance(item, list) and len(item) == 2]
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logging.error(f"履歴ファイルの読み込みに失敗しました: {e}", exc_info=True)
                return []
        return []

    def save_history_to_file(self):
        self._save_history_to_file()

    def _save_history_to_file(self):
        try:
            with open(self.history_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=4)
        except IOError as e:
            logging.error(f"履歴ファイルの保存に失敗しました: {e}", exc_info=True)
            if self.error_callback:
                self.error_callback("履歴保存エラー", f"履歴ファイル '{self.history_file_path}' の保存に失敗しました。")
