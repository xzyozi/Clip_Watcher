import tkinter as tk
from tkinter import messagebox
import logging
from src.core.event_dispatcher import EventDispatcher
from src.utils.error_handler import log_and_show_error
from src.utils.undo_manager import UndoManager
from src.core.commands import UpdateHistoryCommand

logger = logging.getLogger(__name__)

class HistoryEventHandlers:
    def __init__(self, app_instance, event_dispatcher: EventDispatcher, undo_manager: UndoManager):
        self.app = app_instance
        self.event_dispatcher = event_dispatcher
        self.undo_manager = undo_manager

        # Subscribe to events
        self.event_dispatcher.subscribe("HISTORY_COPY_SELECTED", self.handle_copy_selected_history)
        self.event_dispatcher.subscribe("HISTORY_CLEAR_ALL", self.handle_clear_all_history)
        self.event_dispatcher.subscribe("HISTORY_DELETE_SELECTED", self.handle_delete_selected_history)
        self.event_dispatcher.subscribe("HISTORY_DELETE_ALL_UNPINNED", self.handle_delete_all_unpinned_history)
        self.event_dispatcher.subscribe("HISTORY_PIN_UNPIN", self.handle_pin_unpin_history)
        self.event_dispatcher.subscribe("HISTORY_COPY_MERGED", self.handle_copy_selected_as_merged)
        self.event_dispatcher.subscribe("HISTORY_FORMAT_ITEM", self.format_selected_item)
        self.event_dispatcher.subscribe("HISTORY_SEARCH", self.handle_search_history)
        self.event_dispatcher.subscribe("HISTORY_CREATE_QUICK_TASK", self.handle_create_quick_task)
        self.event_dispatcher.subscribe("HISTORY_ITEM_EDITED", self.handle_history_item_edited)
        self.event_dispatcher.subscribe("REQUEST_UNDO_LAST_ACTION", self.undo_manager.undo)
        self.event_dispatcher.subscribe("REQUEST_REDO_LAST_ACTION", self.undo_manager.redo)

    def handle_history_item_edited(self, data):
        try:
            selected_indices = self.app.gui.history_component.listbox.curselection()
            if not selected_indices:
                return
            
            selected_index = selected_indices[0]
            new_text = data['new_text']
            original_text = data['original_text']

            command = UpdateHistoryCommand(
                monitor=self.app.monitor,
                index=selected_index,
                original_text=original_text,
                new_text=new_text
            )
            self.undo_manager.execute_command(command)
            logger.info(f"Executed update command for history item at index {selected_index}.")

        except IndexError:
            logger.warning("Could not update history item: No item selected.")
        except Exception as e:
            log_and_show_error("Error", f"Failed to update history item: {e}", exc_info=True)

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
        try:
            history_data = self.app.monitor.get_history()
            selected_item_content = history_data[selected_indices[0]][0]
            self.app.master.clipboard_clear()
            self.app.master.clipboard_append(selected_item_content)
            logger.info(f"Copied from history: {selected_item_content[:50]}...")
        except IndexError:
            pass

    def handle_clear_all_history(self):
        self.app.monitor.clear_history()
        self.app.gui.update_clipboard_display("", [])
        logger.info("All history cleared.")

    def handle_delete_selected_history(self, selected_indices):
        if not selected_indices:
            logger.warning("No history item selected for deletion.")
            return
        try:
            indices_to_delete = sorted(list(selected_indices), reverse=True)
            for index in indices_to_delete:
                self.app.monitor.delete_history_item(index)
            logger.info(f"Deleted {len(indices_to_delete)} selected history item(s).")
        except Exception as e:
            logger.error(f"Error deleting selected history: {e}")

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

    def handle_pin_unpin_history(self, selected_index):
        if selected_index is None:
            logger.warning("No history item selected for pin/unpin.")
            return
        try:
            history_list = self.app.monitor.get_history()
            if self.app.history_sort_ascending:
                history_list = history_list[::-1]

            item_tuple = history_list[selected_index]
            content, is_pinned = item_tuple

            if is_pinned:
                self.app.monitor.unpin_item(item_tuple)
                logger.info(f"Unpinned: {content[:50]}...")
            else:
                self.app.monitor.pin_item(item_tuple)
                logger.info(f"Pinned: {content[:50]}...")
        except IndexError:
            logger.error("No history item selected for pin/unpin.")
        except Exception as e:
            logger.error(f"Error pinning/unpinning history: {e}")

    def handle_copy_selected_as_merged(self, selected_indices):
        if not selected_indices:
            logger.warning("No history items selected for merging.")
            return
        try:
            merged_content_parts = []
            history_data = self.app.monitor.get_history()
            for index in selected_indices:
                if 0 <= index < len(history_data):
                    merged_content_parts.append(history_data[index][0])
            if merged_content_parts:
                merged_content = "\n".join(merged_content_parts)
                self.app.master.clipboard_clear()
                self.app.master.clipboard_append(merged_content)
                logger.info(f"Copied merged content: {merged_content[:50]}...")
            else:
                logger.warning("No valid history items selected for merging.")
        except Exception as e:
            logger.error(f"Error merging and copying selected history: {e}")

    def format_selected_item(self):
        try:
            selected_indices = self.app.gui.history_component.listbox.curselection()
            if not selected_indices:
                return

            from src.gui.format_dialog import FormatDialog
            
            dialog = self.app.create_toplevel(FormatDialog, self.app.settings_manager)
            selected_plugin = dialog.selected_plugin

            if selected_plugin:
                self.apply_plugin_to_selected_item(selected_plugin)

        except IndexError:
            log_and_show_error("エラー", "フォーマット対象の項目が選択されていません。", exc_info=True)
        except Exception as e:
            log_and_show_error("エラー", f"フォーマット中に予期せぬエラーが発生しました。\n\n{e}", exc_info=True)

    def apply_plugin_to_selected_item(self, plugin_instance):
        try:
            selected_indices = self.app.gui.history_component.listbox.curselection()
            if not selected_indices:
                return

            selected_index = selected_indices[0]

            history_data = self.app.gui.history_data
            if 0 <= selected_index < len(history_data):
                original_text, _ = history_data[selected_index]
                
                processed_text = plugin_instance.process(original_text)

                if processed_text != original_text:
                    command = UpdateHistoryCommand(
                        monitor=self.app.monitor,
                        index=selected_index,
                        original_text=original_text,
                        new_text=processed_text
                    )
                    self.undo_manager.execute_command(command)
                    logger.info(f"Executed format command for item at index {selected_index} with {plugin_instance.name}")
                else:
                    logger.warning(f"Plugin '{plugin_instance.name}' made no changes.")

        except IndexError:
            log_and_show_error("エラー", "フォーマット対象の項目が選択されていません。", exc_info=True)
        except Exception as e:
            log_and_show_error("エラー", f"プラグインの適用中にエラーが発生しました。\n\n{e}", exc_info=True)

    def handle_search_history(self, search_query):
        if search_query:
            filtered_history = self.app.monitor.get_filtered_history(search_query)
            self.app.gui.update_clipboard_display(self.app.monitor.last_clipboard_data, filtered_history)
        else:
            self.app.gui.update_clipboard_display(self.app.monitor.last_clipboard_data, self.app.monitor.get_history())
