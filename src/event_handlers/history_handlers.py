import tkinter as tk
from tkinter import messagebox
import logging
from typing import Optional
from src.core.event_dispatcher import EventDispatcher
from src.utils.error_handler import log_and_show_error
from src.utils.undo_manager import UndoManager
from src.core.commands import UpdateHistoryCommand
from .base_event_handler import BaseEventHandler

logger = logging.getLogger(__name__)

class HistoryEventHandlers(BaseEventHandler):
    def __init__(self, app_instance, event_dispatcher: EventDispatcher, undo_manager: UndoManager):
        self.app = app_instance
        self.undo_manager = undo_manager
        super().__init__(event_dispatcher)

    def _register_handlers(self):
        """Register all event handlers for this class."""
        self.subscribe("HISTORY_COPY_SELECTED", self.handle_copy_selected_history)
        self.subscribe("HISTORY_CLEAR_ALL", self.handle_clear_all_history)
        self.subscribe("HISTORY_DELETE_SELECTED", self.handle_delete_selected_history)
        self.subscribe("HISTORY_DELETE_ALL_UNPINNED", self.handle_delete_all_unpinned_history)
        self.subscribe("HISTORY_PIN_UNPIN", self.handle_pin_unpin_history)
        self.subscribe("HISTORY_COPY_MERGED", self.handle_copy_selected_as_merged)
        self.subscribe("HISTORY_FORMAT_ITEM", self.format_selected_item)
        self.subscribe("HISTORY_SEARCH", self.handle_search_history)
        self.subscribe("HISTORY_CREATE_QUICK_TASK", self.handle_create_quick_task)
        self.subscribe("HISTORY_ITEM_EDITED", self.handle_history_item_edited)
        self.subscribe("REQUEST_UNDO_LAST_ACTION", self.undo_manager.undo)
        self.subscribe("REQUEST_REDO_LAST_ACTION", self.undo_manager.redo)

    def handle_history_item_edited(self, data):
        try:
            history_component = self.app.gui.history_component
            selected_indices = history_component.listbox.curselection()
            if not selected_indices:
                return
            
            first_index = selected_indices[0]
            # Ensure we have the ID for the command
            item_id = history_component.get_ids_for_indices((first_index,))[0]
            
            new_text = data['new_text']
            # original_text is passed in the event data, which is correct
            original_text = data['original_text']

            command = UpdateHistoryCommand(
                monitor=self.app.monitor,
                item_id=item_id,
                original_text=original_text,
                new_text=new_text
            )
            self.undo_manager.execute_command(command)
            logger.info(f"Executed update command for history item with ID {item_id}.")

        except (IndexError, KeyError):
            logger.warning("Could not update history item: No item selected or ID not found.")
        except Exception as e:
            log_and_show_error("Error", f"Failed to update history item: {e}", exc_info=True)

    def handle_create_quick_task(self, item_ids: list[float]):
        if not item_ids:
            return
        
        history_data = self.app.monitor.get_history()
        id_to_content = {item[2]: item[0] for item in history_data}
        
        tasks = [id_to_content[item_id] for item_id in item_ids if item_id in id_to_content]

        if tasks:
            from src.gui.windows.quick_task_dialog import QuickTaskDialog
            QuickTaskDialog(self.app.master, self.app, tasks)

    def handle_copy_selected_history(self, item_ids: list[float]):
        if not item_ids:
            return
        try:
            first_id = item_ids[0]
            history_data = self.app.monitor.get_history()
            
            selected_item_content = None
            for content, _, item_id in history_data:
                if item_id == first_id:
                    selected_item_content = content
                    break
            
            if selected_item_content is not None:
                self.app.master.clipboard_clear()
                self.app.master.clipboard_append(selected_item_content)
                logger.info(f"Copied from history: {selected_item_content[:50]}...")
            else:
                logger.warning(f"Could not find item with ID {first_id} to copy.")
        except Exception as e:
            logger.error(f"Error copying selected history: {e}", exc_info=True)

    def handle_clear_all_history(self):
        self.app.monitor.clear_history()
        self.app.gui.update_clipboard_display("", [])
        logger.info("All history cleared.")

    def handle_delete_selected_history(self, item_ids: list[float]):
        if not item_ids:
            logger.warning("No history item selected for deletion.")
            return
        try:
            # No need to sort, just iterate and delete by ID
            for item_id in item_ids:
                self.app.monitor.delete_history_item_by_id(item_id)
            logger.info(f"Deleted {len(item_ids)} selected history item(s).")
        except Exception as e:
            logger.error(f"Error deleting selected history: {e}", exc_info=True)

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

    def handle_pin_unpin_history(self, item_id: Optional[float]):
        if item_id is None:
            logger.warning("No history item selected for pin/unpin.")
            return
        try:
            # Find the item by ID to check its current state
            history_list = self.app.monitor.get_history()
            item_tuple = None
            for item in history_list:
                if item[2] == item_id:
                    item_tuple = item
                    break
            
            if item_tuple is None:
                logger.error(f"Could not find history item with ID {item_id} for pin/unpin.")
                return

            content, is_pinned, _ = item_tuple

            if is_pinned:
                self.app.monitor.unpin_item_by_id(item_id)
                logger.info(f"Unpinned: {content[:50]}...")
            else:
                self.app.monitor.pin_item_by_id(item_id)
                logger.info(f"Pinned: {content[:50]}...")
        except Exception as e:
            logger.error(f"Error pinning/unpinning history: {e}", exc_info=True)

    def handle_copy_selected_as_merged(self, item_ids: list[float]):
        if not item_ids:
            logger.warning("No history items selected for merging.")
            return
        try:
            history_data = self.app.monitor.get_history()
            id_to_content = {item[2]: item[0] for item in history_data}
            
            merged_content_parts = [id_to_content[item_id] for item_id in item_ids if item_id in id_to_content]
            
            if merged_content_parts:
                merged_content = "\n".join(merged_content_parts)
                self.app.master.clipboard_clear()
                self.app.master.clipboard_append(merged_content)
                logger.info(f"Copied merged content: {merged_content[:50]}...")
            else:
                logger.warning("No valid history items selected for merging.")
        except Exception as e:
            logger.error(f"Error merging and copying selected history: {e}", exc_info=True)

    def format_selected_item(self):
        try:
            selected_indices = self.app.gui.history_component.listbox.curselection()
            if not selected_indices:
                return

            from src.gui.dialogs.format_dialog import FormatDialog
            
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