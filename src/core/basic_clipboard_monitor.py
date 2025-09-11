
import time
import threading
import tkinter as tk
import ctypes
import ctypes.wintypes
import winsound

class ClipboardMonitor:
    def __init__(self, tk_root, history_limit=50, excluded_apps=None):
        self.tk_root = tk_root
        self.update_callback = None
        self.last_clipboard_data = ""
        self._running = False
        self.monitor_thread = None
        self.history = []
        self.history_limit = history_limit
        self.excluded_apps = excluded_apps if excluded_apps is not None else []
    # --- Windows APIを使ってアクティブプロセス名を取得 ---
    def get_active_process_name(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        process_handle = kernel32.OpenProcess(0x0410, False, pid.value)  # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
        if not process_handle:
            return None

        exe_name = (ctypes.c_char * 260)()
        psapi.GetModuleBaseNameA(process_handle, None, exe_name, 260)
        kernel32.CloseHandle(process_handle)

        return exe_name.value.decode(errors="ignore")

    def set_history_limit(self, limit):
        self.history_limit = limit
        if len(self.history) > self.history_limit:
            self.history = self.history[:self.history_limit]
            self._trigger_gui_update()

    def set_excluded_apps(self, excluded_apps):
        self.excluded_apps = excluded_apps

    def set_gui_update_callback(self, callback):
        self.update_callback = callback

    def _monitor_clipboard(self):
        print("クリップボード監視を開始します")
        while self._running:
            try:
                try:
                    # スレッドセーフにクリップボードにアクセス
                    self.tk_root.after(0, self._check_clipboard)
                    time.sleep(0.5)  # 500ms間隔で監視
                except RuntimeError as e:
                    print(f"Tkinterランタイムエラー: {str(e)}")
                    time.sleep(1)  # エラー時は待機時間を延長
                except Exception as e:
                    print(f"クリップボード監視エラー: {str(e)}")
                    time.sleep(1)
            except Exception as e:
                print(f"重大なエラー: {str(e)}")
                break

    def _decode_clipboard_data(self, data):
        """クリップボードデータのデコード処理"""
        if isinstance(data, bytes):
            # 複数のエンコーディングを試行
            encodings = ['utf-8', 'shift-jis', 'cp932', 'euc-jp', 'latin1']
            for encoding in encodings:
                try:
                    return data.decode(encoding)
                except UnicodeDecodeError:
                    continue
            # すべて失敗した場合は、バイトを無視して強制的にデコード
            return data.decode('utf-8', errors='ignore')
        elif isinstance(data, str):
            # If it's already a string, try to normalize it to valid UTF-8
            try:
                return data.encode('utf-8', errors='surrogateescape').decode('utf-8', errors='ignore')
            except Exception:
                return data # Fallback if normalization fails
        return str(data) # Ensure it's a string

    def _check_clipboard(self):
        """スレッドセーフなクリップボードチェック処理"""
        try:
            clipboard_data = ""
            try:
                # クリップボードの内容を保持
                current_content = self.tk_root.clipboard_get()
                
                # Check for excessively large content before processing
                # A heuristic limit, adjust as needed. For example, 1MB of text.
                # Note: len() counts characters, not bytes. A single character can be multiple bytes.
                # This check is a rough estimate.
                if len(current_content) > 1024 * 1024: # If content is larger than 1MB (approx)
                    print("Warning: Clipboard content is excessively large. Skipping to prevent potential issues.")
                    return

                # デコード処理 (assuming clipboard_get returns a string)
                # Use the robust _decode_clipboard_data
                try:
                    clipboard_data = self._decode_clipboard_data(current_content)
                except Exception as e:
                    print(f"クリップボードデータ正規化エラー: {str(e)}")
                    # Fallback to direct string if normalization fails
                    clipboard_data = str(current_content)

            except tk.TclError as e:
                # クリップボードが空または利用不可の場合は無視
                # Also catches errors when clipboard content is too large for tkinter to handle
                if "CLIPBOARD_GET" in str(e) and "too large" in str(e).lower():
                    print(f"Warning: Clipboard content too large for Tkinter. Skipping. Error: {e}")
                else:
                    # print(f"Tkinterクリップボードエラー: {str(e)}") # Uncomment for debugging other TclErrors
                    pass
                return
            except Exception as e:
                print(f"クリップボード取得または初期デコードエラー: {str(e)}")
                return

            # 更新の確認と処理
            if clipboard_data and clipboard_data != self.last_clipboard_data:
                active_process = self.get_active_process_name()
                print(f"クリップボードの更新を検出 - プロセス: {active_process}")
                
                if active_process in self.excluded_apps:
                    print(f"除外アプリからのコピーのため無視: {active_process}")
                    return
                    
                self.history.insert(0, (clipboard_data, False))
                if len(self.history) > self.history_limit:
                    unpinned = [i for i, (_, is_pinned) in enumerate(self.history) if not is_pinned]
                    if unpinned:
                        del self.history[unpinned[-1]]
    
                self.last_clipboard_data = clipboard_data
                self._trigger_gui_update()

        except Exception as e:
            print(f"予期せぬエラー: {str(e)}")
            import traceback
            print(traceback.format_exc())

    def _play_notification_sound(self):
        winsound.Beep(1000, 200)  # 周波数1000Hz, 200ms

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

    def pin_item(self, index):
        current_display_history = self.get_history()
        if 0 <= index < len(current_display_history):
            item_to_pin = current_display_history[index]
            for i, (content, is_pinned) in enumerate(self.history):
                if (content, is_pinned) == item_to_pin:
                    self.history[i] = (content, True)
                    break
            self._trigger_gui_update()

    def unpin_item(self, index):
        current_display_history = self.get_history()
        if 0 <= index < len(current_display_history):
            item_to_unpin = current_display_history[index]
            for i, (content, is_pinned) in enumerate(self.history):
                if (content, is_pinned) == item_to_unpin:
                    self.history[i] = (content, False)
                    break
            self._trigger_gui_update()

    def delete_all_unpinned_history(self):
        self.history = [item for item in self.history if item[1]]
        self._trigger_gui_update()
        print("Monitor: Deleted all unpinned history.")

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
                if len(self.history) >  self.history_limit:
                    self.history.pop()
        self._trigger_gui_update()

    def get_filtered_history(self, query):
        filtered_raw = [item for item in self.history if query.lower() in item[0].lower()]
        
        pinned = [item for item in filtered_raw if item[1]]
        unpinned = [item for item in filtered_raw if not item[1]]
        return pinned + unpinned