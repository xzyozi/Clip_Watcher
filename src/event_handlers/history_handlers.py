import tkinter as tk
import logging
from src.event_dispatcher import EventDispatcher
from src.utils.error_handler import log_and_show_error

logger = logging.getLogger(__name__)

class HistoryEventHandlers:
    def __init__(self, app_instance, event_dispatcher: EventDispatcher):
        self.app = app_instance
        self.event_dispatcher = event_dispatcher

        # Subscribe to events
        self.event_dispatcher.subscribe("HISTORY_COPY_SELECTED", self.handle_copy_selected_history)
        self.event_dispatcher.subscribe("HISTORY_CLEAR_ALL", self.handle_clear_all_history)
        self.event_dispatcher.subscribe("HISTORY_DELETE_SELECTED", self.handle_delete_selected_history)
        self.event_dispatcher.subscribe("HISTORY_DELETE_ALL_UNPINNED", self.handle_delete_all_unpinned_history)
        self.event_dispatcher.subscribe("HISTORY_PIN_UNPIN", self.handle_pin_unpin_history)
        self.event_dispatcher.subscribe("HISTORY_COPY_MERGED", self.handle_copy_selected_as_merged)
        self.event_dispatcher.subscribe("HISTORY_FORMAT_ITEM", self.format_selected_item)
        self.event_dispatcher.subscribe("HISTORY_UNDO_FORMAT", self.undo_last_format)
        self.event_dispatcher.subscribe("HISTORY_SEARCH", self.handle_search_history)
        self.event_dispatcher.subscribe("HISTORY_CREATE_QUICK_TASK", self.handle_create_quick_task)

    def handle_create_quick_task(self, selected_indices):
        if not selected_indices:
            return
        
        tasks = []
        for index in selected_indices:
            content, _ = self.app.monitor.get_history()[index]
            tasks.append(content)

        if tasks:
            from src.gui.quick_task_dialog import QuickTaskDialog
            dialog = QuickTaskDialog(self.app.master, self.app, tasks)

    def handle_copy_selected_history(self, selected_indices):
        if not selected_indices:
            return
        selected_index = selected_indices[0]
        self.event_dispatcher.dispatch("REQUEST_COPY_HISTORY_ITEM", selected_index)

    def handle_clear_all_history(self):
        self.event_dispatcher.dispatch("REQUEST_CLEAR_ALL_HISTORY")

    def handle_delete_selected_history(self, selected_indices):
        if not selected_indices:
            logger.warn("No history item selected for deletion.")
            return
        indices_to_delete = sorted(list(selected_indices), reverse=True)
        self.event_dispatcher.dispatch("REQUEST_DELETE_HISTORY_ITEMS", indices_to_delete)

    def handle_delete_all_unpinned_history(self):
        self.event_dispatcher.dispatch("REQUEST_DELETE_ALL_UNPINNED_HISTORY")

    def handle_pin_unpin_history(self, selected_index):
        if selected_index is None:
            logger.warn("No history item selected for pin/unpin.")
            return
        self.event_dispatcher.dispatch("REQUEST_PIN_UNPIN_HISTORY_ITEM", selected_index)

    def handle_copy_selected_as_merged(self, selected_indices):
        if not selected_indices:
            logger.warn("No history items selected for merging.")
            return
        self.event_dispatcher.dispatch("REQUEST_COPY_MERGED_HISTORY_ITEMS", selected_indices)

    def format_selected_item(self):
        """Opens a dialog to choose a plugin and applies it to the selected history item."""
        try:
            selected_indices = self.app.gui.history_listbox.curselection()
            if not selected_indices:
                return

            selected_index = selected_indices[0]

            from src.gui.format_dialog import FormatDialog
            
            dialog = FormatDialog(self.app.master, self.app, self.app.settings_manager)
            selected_plugin = dialog.selected_plugin

            if selected_plugin:
                # Call the generic apply_plugin_to_selected_item with the chosen plugin
                self.apply_plugin_to_selected_item(selected_plugin)

        except IndexError:
            log_and_show_error("エラー", "フォーマット対象の項目が選択されていません。", exc_info=True)
        except Exception as e:
            log_and_show_error("エラー", f"フォーマット中に予期せぬエラーが発生しました。\n\n{e}", exc_info=True)

    def apply_plugin_to_selected_item(self, plugin_instance):
        """Applies a specific plugin to the selected history item."""
        try:
            selected_indices = self.app.gui.history_listbox.curselection()
            if not selected_indices:
                return

            selected_index = selected_indices[0]

            history_data = self.app.gui.history_data
            if 0 <= selected_index < len(history_data):
                original_text, _ = history_data[selected_index]
                
                processed_text = plugin_instance.process(original_text)

                if processed_text != original_text:
                    self.app.last_formatted_info = {
                        'index': selected_index,
                        'original_text': original_text,
                        'processed_text': processed_text
                    }
                    
                    self.app.monitor.update_history_item(selected_index, processed_text)
                    
                    # Manually update the top display
                    self.app.gui.clipboard_text_widget.config(state=tk.NORMAL)
                    self.app.gui.clipboard_text_widget.delete(1.0, tk.END)
                    self.app.gui.clipboard_text_widget.insert(tk.END, processed_text)
                    self.app.gui.clipboard_text_widget.config(state=tk.DISABLED)

                    self.app.gui.enable_undo_button()
                    logger.info(f"Formatted item at index {selected_index} with {plugin_instance.name}")
                else:
                    logger.warn(f"Plugin '{plugin_instance.name}' made no changes.")
                    self.app.last_formatted_info = None
                    self.app.gui.disable_undo_button()

        except IndexError:
            log_and_show_error("エラー", "フォーマット対象の項目が選択されていません。", exc_info=True)
        except Exception as e:
            log_and_show_error("エラー", f"プラグインの適用中にエラーが発生しました。\n\n{e}", exc_info=True)

    def undo_last_format(self):
        """Reverts the last formatting operation."""
        if not hasattr(self.app, 'last_formatted_info') or not self.app.last_formatted_info:
            logger.warn("No format operation to undo.")
            return

        try:
            info = self.app.last_formatted_info
            index = info['index']
            original_text = info['original_text']
            
            current_text, _ = self.app.gui.history_data[index]
            if current_text == info['processed_text']:
                self.app.monitor.update_history_item(index, original_text)

                # Manually update the top display
                self.app.gui.clipboard_text_widget.config(state=tk.NORMAL)
                self.app.gui.clipboard_text_widget.delete(1.0, tk.END)
                self.app.gui.clipboard_text_widget.insert(tk.END, original_text)
                self.app.gui.clipboard_text_widget.config(state=tk.DISABLED)

                logger.info(f"Undo format for item at index {index}")
            else:
                logger.warn("Cannot undo: The item has been modified since formatting.")

        except Exception as e:
            log_and_show_error("エラー", f"元に戻す処理中にエラーが発生しました。\n\n{e}", exc_info=True)
        finally:
            self.app.last_formatted_info = None
            self.app.gui.disable_undo_button()

    def handle_search_history(self, search_query):
        self.event_dispatcher.dispatch("REQUEST_SEARCH_HISTORY", search_query)
