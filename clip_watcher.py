import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sys
import traceback
from src.clipboard_monitor import ClipboardMonitor
from src.gui.main_gui import ClipWatcherGUI
from src.gui import menu_bar
from src.settings_manager import SettingsManager
from src.plugin_manager import PluginManager
from src.gui.settings_window import SettingsWindow
from src.event_handlers.history_handlers import HistoryEventHandlers
from src.event_handlers.file_handlers import FileEventHandlers
from src.event_handlers.settings_handlers import SettingsEventHandlers
from src.fixed_phrases_manager import FixedPhrasesManager

# Define history file path
if sys.platform == "win32":
    APP_DATA_DIR = os.path.join(os.environ['APPDATA'], 'ClipWatcher')
else:
    APP_DATA_DIR = os.path.join(os.path.expanduser('~'), '.clipwatcher')

os.makedirs(APP_DATA_DIR, exist_ok=True)
HISTORY_FILE_PATH = os.path.join(APP_DATA_DIR, 'history.json')


from src.base_application import BaseApplication

class Application(BaseApplication):
    def __init__(self, master, settings_manager, monitor, fixed_phrases_manager, plugin_manager, event_dispatcher):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.settings_manager = settings_manager
        self.monitor = monitor
        self.fixed_phrases_manager = fixed_phrases_manager
        self.plugin_manager = plugin_manager
        self.event_dispatcher = event_dispatcher
        self.undo_stack = []
        self.redo_stack = []
        self.history_sort_ascending = False
        
        # Initialize event handlers first
        self.history_handlers = HistoryEventHandlers(self, event_dispatcher)
        self.file_handlers = FileEventHandlers(event_dispatcher)
        self.settings_handlers = SettingsEventHandlers(event_dispatcher)
        
        self.gui = ClipWatcherGUI(master, self)
        self.monitor.set_gui_update_callback(self.gui.update_clipboard_display)
        self.monitor.set_error_callback(self.show_error_message)

        self.monitor.start()

        self.menubar = menu_bar.create_menu_bar(master, self)
        master.config(menu=self.menubar)

        self.event_dispatcher.subscribe("REQUEST_CLEAR_ALL_HISTORY", self.on_request_clear_all_history)
        self.event_dispatcher.subscribe("REQUEST_DELETE_ALL_UNPINNED_HISTORY", self.on_request_delete_all_unpinned_history)
        self.event_dispatcher.subscribe("REQUEST_QUIT", self.on_request_quit)
        self.event_dispatcher.subscribe("REQUEST_EXPORT_HISTORY", self.on_request_export_history)
        self.event_dispatcher.subscribe("REQUEST_IMPORT_HISTORY", self.on_request_import_history)
        self.event_dispatcher.subscribe("REQUEST_ALWAYS_ON_TOP", self.on_request_always_on_top)
        self.event_dispatcher.subscribe("REQUEST_SET_THEME", self.on_request_set_theme)
        self.event_dispatcher.subscribe("REQUEST_DELETE_HISTORY_ITEMS", self.on_request_delete_history_items)
        self.event_dispatcher.subscribe("REQUEST_PIN_UNPIN_HISTORY_ITEM", self.on_request_pin_unpin_history_item)
        self.event_dispatcher.subscribe("REQUEST_COPY_HISTORY_ITEM", self.on_request_copy_history_item)
        self.event_dispatcher.subscribe("REQUEST_COPY_MERGED_HISTORY_ITEMS", self.on_request_copy_merged_history_items)
        self.event_dispatcher.subscribe("REQUEST_SEARCH_HISTORY", self.on_request_search_history)
        self.event_dispatcher.subscribe("APPLY_INITIAL_SETTINGS", self.on_apply_initial_settings)
        self.event_dispatcher.subscribe("HISTORY_TOGGLE_SORT", self.on_toggle_history_sort)
        self.event_dispatcher.dispatch("APPLY_INITIAL_SETTINGS")

    def on_toggle_history_sort(self):
        """Toggles the history sort order and refreshes the GUI."""
        self.history_sort_ascending = not self.history_sort_ascending
        
        # Update button text to reflect the NEW sort order
        if self.history_sort_ascending:
            self.gui.sort_button.config(text="Sort: Asc")
        else:
            self.gui.sort_button.config(text="Sort: Desc")

        # Trigger a GUI update to reflect the new sort order
        self.gui.update_clipboard_display(self.monitor.last_clipboard_data, self.monitor.get_history())
        print(f"History sort order set to {'ascending' if self.history_sort_ascending else 'descending'}")

    def on_apply_initial_settings(self):
        self.settings_manager.apply_settings(self)

    def on_request_clear_all_history(self):
        self.monitor.clear_history()
        self.gui.update_clipboard_display("", [])
        print("All history cleared.")

    def on_request_delete_all_unpinned_history(self):
        if messagebox.askyesno(
            "確認 (Confirm)",
            "ピン留めされていないすべての履歴を削除しますか？\nこの操作は元に戻せません。",
            parent=self.master
        ):
            self.monitor.delete_all_unpinned_history()
            messagebox.showinfo("完了", "ピン留めされていない履歴をすべて削除しました。", parent=self.master)
        else:
            messagebox.showinfo("キャンセル", "操作をキャンセルしました。", parent=self.master)

    def on_request_quit(self):
        self.stop_monitor()
        self.master.quit()

    def on_request_export_history(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="履歴をエクスポート (Export History)"
        )
        if file_path:
            try:
                history_content = self.monitor.get_history()
                with open(file_path, "w", encoding="utf-8") as f:
                    for item_tuple in history_content:
                        f.write(item_tuple[0] + "\n---")
                messagebox.showinfo("エクスポート完了", f"履歴を以下のファイルにエクスポートしました:\n{file_path}")
            except Exception as e:
                messagebox.showerror("エクスポートエラー", f"履歴のエクスポート中にエラーが発生しました:\n{e}")

    def on_request_import_history(self):
        file_path = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="履歴をインポート (Import History)"
        )
        if file_path:
            try:
                imported_history = []
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    raw_items = content.split("---")
                    imported_history = [item.strip() for item in raw_items if item.strip()]
                
                self.monitor.import_history(imported_history)
                messagebox.showinfo("インポート完了", f"履歴を以下のファイルからインポートしました:\n{file_path}")
            except Exception as e:
                messagebox.showerror("インポートエラー", f"履歴のインポート中にエラーが発生しました:\n{e}")

    def on_request_always_on_top(self, always_on_top):
        self.master.attributes('-topmost', always_on_top)
        print(f"Always on Top set to: {always_on_top}")

    def on_request_set_theme(self, theme_name):
        self.gui.apply_theme(theme_name)
        print(f"Theme set to: {theme_name}")

    def on_request_delete_history_items(self, indices_to_delete):
        try:
            for index in indices_to_delete:
                self.monitor.delete_history_item(index)
            print(f"Deleted {len(indices_to_delete)} selected history item(s).")
        except Exception as e:
            print(f"Error deleting selected history: {e}")

    def on_request_pin_unpin_history_item(self, selected_index):
        try:
            # Get the history list in the same order as the GUI is displaying it
            history_list = self.monitor.get_history()
            if self.history_sort_ascending:
                history_list = history_list[::-1]

            # Get the correct item tuple
            item_tuple = history_list[selected_index]
            content, is_pinned = item_tuple

            # Call the monitor with the unambiguous item tuple
            if is_pinned:
                self.monitor.unpin_item(item_tuple)
                print(f"Unpinned: {content[:50]}...")
            else:
                self.monitor.pin_item(item_tuple)
                print(f"Pinned: {content[:50]}...")
        except IndexError:
            print("No history item selected for pin/unpin.")
        except Exception as e:
            print(f"Error pinning/unpinning history: {e}")

    def on_request_copy_history_item(self, selected_index):
        try:
            history_data = self.monitor.get_history()
            selected_item_content = history_data[selected_index][0]
            self.master.clipboard_clear()
            self.master.clipboard_append(selected_item_content)
            print(f"Copied from history (Tkinter): {selected_item_content[:50]}...")
        except IndexError:
            pass

    def on_request_copy_merged_history_items(self, selected_indices):
        try:
            if not selected_indices:
                print("No history items selected for merging.")
                return
            merged_content_parts = []
            history_data = self.monitor.get_history()
            for index in selected_indices:
                if 0 <= index < len(history_data):
                    merged_content_parts.append(history_data[index][0])
            if merged_content_parts:
                merged_content = "\n".join(merged_content_parts)
                self.master.clipboard_clear()
                self.master.clipboard_append(merged_content)
                print(f"Copied merged content: {merged_content[:50]}...")
            else:
                print("No valid history items selected for merging.")
        except Exception as e:
            print(f"Error merging and copying selected history: {e}")

    def on_request_search_history(self, search_query):
        if search_query:
            filtered_history = self.monitor.get_filtered_history(search_query)
            self.gui.update_clipboard_display(self.monitor.last_clipboard_data, filtered_history)
        else:
            self.gui.update_clipboard_display(self.monitor.last_clipboard_data, self.monitor.get_history())

    def open_settings_window(self):
        settings_window = SettingsWindow(self.master, self.settings_manager, self)
        settings_window.grab_set()

    def show_error_message(self, title, message):
        messagebox.showerror(title, message)

    def stop_monitor(self):
        self.monitor.stop()

    def on_closing(self):
        self.stop_monitor()
        self.monitor.save_history_to_file() # Save history on exit
        self.master.destroy()










if __name__ == "__main__":
    try:
        from src.utils.logging_config import setup_logging
        from src.application_builder import ApplicationBuilder

        # Setup logging at the very beginning
        logger = setup_logging()
        
        logger.info("アプリケーションを開始します")
        
        root = tk.Tk()
    
        builder = ApplicationBuilder()
        app = builder.with_settings()\
                     .with_fixed_phrases_manager()\
                     .with_plugin_manager()\
                     .with_event_dispatcher()\
                     .with_clipboard_monitor(root, HISTORY_FILE_PATH)\
                     .build(root)
               
        logger.info("アプリケーションの初期化が完了しました")
        
        root.mainloop()
    except Exception as e:
        if 'logger' in locals():
            logger.error(f"アプリケーション起動エラー: {str(e)}", exc_info=True)
        else:
            print(f"アプリケーション起動エラー: {str(e)}")
        traceback.print_exc()