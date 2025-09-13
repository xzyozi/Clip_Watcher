import tkinter as tk
from tkinter import messagebox

class HistoryEventHandlers:
    def __init__(self, app_instance):
        self.app = app_instance

    def handle_copy_selected_history(self):
        try:
            selected_index = self.app.gui.history_listbox.curselection()[0]
            history_data = self.app.monitor.get_history()
            selected_item_content = history_data[selected_index][0]
            self.app.master.clipboard_clear()
            self.app.master.clipboard_append(selected_item_content)
            print(f"Copied from history (Tkinter): {selected_item_content[:50]}...")
        except IndexError:
            pass

    def handle_clear_all_history(self):
        self.app.monitor.clear_history()
        self.app.gui.update_clipboard_display("", [])
        print("All history cleared.")

    def handle_delete_selected_history(self):
        try:
            selected_indices = self.app.gui.history_listbox.curselection()
            if not selected_indices:
                print("No history item selected for deletion.")
                return
            indices_to_delete = sorted(list(selected_indices), reverse=True)
            for index in indices_to_delete:
                self.app.monitor.delete_history_item(index)
            print(f"Deleted {len(selected_indices)} selected history item(s).")
        except Exception as e:
            print(f"Error deleting selected history: {e}")

    def handle_delete_all_unpinned_history(self):
        if messagebox.askyesno(
            "確認 (Confirm)",
            "ピン留めされていないすべての履歴を削除しますか？\nこの操作は元に戻せません。",
            parent=self.app.master
        ):
            self.app.monitor.delete_all_unpinned_history()
            messagebox.showinfo("完了", "ピン留めされていない履歴をすべて削除しました。", parent=self.app.master)
        else:
            messagebox.showinfo("キャンセル", "操作をキャンセルしました。", parent=self.app.master)

    def handle_pin_unpin_history(self):
        try:
            selected_index = self.app.gui.history_listbox.curselection()[0]
            item_tuple = self.app.monitor.get_history()[selected_index]
            content, is_pinned = item_tuple
            if is_pinned:
                self.app.monitor.unpin_item(selected_index)
                print(f"Unpinned: {content[:50]}...")
            else:
                self.app.monitor.pin_item(selected_index)
                print(f"Pinned: {content[:50]}...")
        except IndexError:
            print("No history item selected for pin/unpin.")
        except Exception as e:
            print(f"Error pinning/unpinning history: {e}")

    def handle_copy_selected_as_merged(self):
        try:
            selected_indices = self.app.gui.history_listbox.curselection()
            if not selected_indices:
                print("No history items selected for merging.")
                return
            merged_content_parts = []
            history_data = self.app.monitor.get_history()
            for index in selected_indices:
                if 0 <= index < len(history_data):
                    merged_content_parts.append(history_data[index][0])
            if merged_content_parts:
                merged_content = "\n".join(merged_content_parts)
                self.app.master.clipboard_clear()
                self.app.master.clipboard_append(merged_content)
                print(f"Copied merged content: {merged_content[:50]}...")
            else:
                print("No valid history items selected for merging.")
        except Exception as e:
            print(f"Error merging and copying selected history: {e}")

    def format_selected_item(self):
        """Opens a dialog to choose a plugin and applies it to the selected history item."""
        try:
            selected_indices = self.app.gui.history_listbox.curselection()
            if not selected_indices:
                return

            selected_index = selected_indices[0]

            from src.gui.format_dialog import FormatDialog
            
            dialog = FormatDialog(self.app.master, self.app.plugin_manager)
            selected_plugin = dialog.selected_plugin

            if selected_plugin:
                history_data = self.app.gui.history_data
                if 0 <= selected_index < len(history_data):
                    original_text, _ = history_data[selected_index]
                    
                    processed_text = selected_plugin.process(original_text)

                    if processed_text != original_text:
                        self.app.last_formatted_info = {
                            'index': selected_index,
                            'original_text': original_text,
                            'processed_text': processed_text
                        }
                        
                        self.app.monitor.update_history_item(selected_index, processed_text)
                        self.app.gui.enable_undo_button()
                        print(f"Formatted item at index {selected_index} with {selected_plugin.name}")
                    else:
                        print(f"Plugin '{selected_plugin.name}' made no changes.")
                        self.app.last_formatted_info = None
                        self.app.gui.disable_undo_button()

        except IndexError:
            print("No item selected for formatting.")
        except Exception as e:
            print(f"Error during formatting: {e}")

    def undo_last_format(self):
        """Reverts the last formatting operation."""
        if not hasattr(self.app, 'last_formatted_info') or not self.app.last_formatted_info:
            print("No format operation to undo.")
            return

        try:
            info = self.app.last_formatted_info
            index = info['index']
            original_text = info['original_text']
            
            current_text, _ = self.app.gui.history_data[index]
            if current_text == info['processed_text']:
                self.app.monitor.update_history_item(index, original_text)
                print(f"Undo format for item at index {index}")
            else:
                print("Cannot undo: The item has been modified since formatting.")

        except Exception as e:
            print(f"Error during undo: {e}")
        finally:
            self.app.last_formatted_info = None
            self.app.gui.disable_undo_button()

    def handle_search_history(self, search_query):
        if search_query:
            filtered_history = self.app.monitor.get_filtered_history(search_query)
            self.app.gui.update_history_display(filtered_history)
        else:
            self.app.gui.update_history_display(self.app.monitor.get_history())