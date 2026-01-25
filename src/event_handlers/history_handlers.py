from __future__ import annotations

import logging
from tkinter import messagebox
from typing import TYPE_CHECKING, Any

from src.core.commands import UpdateHistoryCommand
from src.core.event_dispatcher import EventDispatcher
from src.utils.error_handler import log_and_show_error
from src.utils.undo_manager import UndoManager

from .base_event_handler import BaseEventHandler

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication
    from src.gui.components.history_list_component import HistoryListComponent
    from src.plugins.base_plugin import Plugin


logger = logging.getLogger(__name__)

class HistoryEventHandlers(BaseEventHandler):
    def __init__(self, app_instance: BaseApplication, event_dispatcher: EventDispatcher, undo_manager: UndoManager) -> None:
        self.app = app_instance
        self.undo_manager = undo_manager
        super().__init__(event_dispatcher)

    def _register_handlers(self) -> None:
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

    def handle_history_item_edited(self, data: dict[str, Any]) -> None:
        try:
            history_component: HistoryListComponent = self.app.gui.history_component # type: ignore
            selected_indices: tuple[int, ...] = history_component.listbox.curselection() # type: ignore
            if not selected_indices:
                return

            first_index: int = selected_indices[0]
            # Ensure we have the ID for the command
            item_id: float = history_component.get_ids_for_indices((first_index,))[0]

            new_text: str = data['new_text']
            # original_text is passed in the event data, which is correct
            original_text: str = data['original_text']

            command = UpdateHistoryCommand(
                monitor=self.app.monitor, # type: ignore
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

    def handle_create_quick_task(self, item_ids: list[float]) -> None:
        if not item_ids:
            return

        history_data: list[tuple[str, bool, float]] = self.app.monitor.get_history() # type: ignore
        id_to_content: dict[float, str] = {item[2]: item[0] for item in history_data}

        tasks: list[str] = [id_to_content[item_id] for item_id in item_ids if item_id in id_to_content]

        if tasks:
            from src.gui.windows.quick_task_dialog import QuickTaskDialog
            QuickTaskDialog(self.app.master, self.app, tasks) # type: ignore

    def handle_copy_selected_history(self, item_ids: list[float]) -> None:
        if not item_ids:
            return
        try:
            first_id: float = item_ids[0]
            history_data: list[tuple[str, bool, float]] = self.app.monitor.get_history() # type: ignore

            selected_item_content: str | None = None
            for content, _, item_id in history_data:
                if item_id == first_id:
                    selected_item_content = content
                    break

            if selected_item_content is not None:
                self.app.master.clipboard_clear() # type: ignore
                self.app.master.clipboard_append(selected_item_content) # type: ignore
                logger.info(f"Copied from history: {selected_item_content[:50]}...")
            else:
                logger.warning(f"Could not find item with ID {first_id} to copy.")
        except Exception as e:
            logger.error(f"Error copying selected history: {e}", exc_info=True)

    def handle_clear_all_history(self) -> None:
        self.app.monitor.clear_history() # type: ignore
        self.app.gui.update_clipboard_display("", []) # type: ignore
        logger.info("All history cleared.")

    def handle_delete_selected_history(self, item_ids: list[float]) -> None:
        if not item_ids:
            logger.warning("No history item selected for deletion.")
            return
        try:
            # No need to sort, just iterate and delete by ID
            for item_id in item_ids:
                self.app.monitor.delete_history_item_by_id(item_id) # type: ignore
            logger.info(f"Deleted {len(item_ids)} selected history item(s).")
        except Exception as e:
            logger.error(f"Error deleting selected history: {e}", exc_info=True)

    def handle_delete_all_unpinned_history(self) -> None:
        if messagebox.askyesno(
            "確認 (Confirm)",
            "ピン留めされていないすべての履歴を削除しますか？\nこの操作は元に戻せません。",
            parent=self.app.master # type: ignore
        ):
            self.app.monitor.delete_all_unpinned_history() # type: ignore
            messagebox.showinfo("完了", "ピン留めされていない履歴をすべて削除しました。", parent=self.app.master) # type: ignore
        else:
            messagebox.showinfo("キャンセル", "操作をキャンセルしました。", parent=self.app.master) # type: ignore

    def handle_pin_unpin_history(self, item_id: float | None) -> None:
        if item_id is None:
            logger.warning("No history item selected for pin/unpin.")
            return
        try:
            # Find the item by ID to check its current state
            history_list: list[tuple[str, bool, float]] = self.app.monitor.get_history() # type: ignore
            item_tuple: tuple[str, bool, float] | None = None
            for item in history_list:
                if item[2] == item_id:
                    item_tuple = item
                    break

            if item_tuple is None:
                logger.error(f"Could not find history item with ID {item_id} for pin/unpin.")
                return

            content, is_pinned, _ = item_tuple

            if is_pinned:
                self.app.monitor.unpin_item_by_id(item_id) # type: ignore
                logger.info(f"Unpinned: {content[:50]}...")
            else:
                self.app.monitor.pin_item_by_id(item_id) # type: ignore
                logger.info(f"Pinned: {content[:50]}...")
        except Exception as e:
            logger.error(f"Error pinning/unpinning history: {e}", exc_info=True)

    def handle_copy_selected_as_merged(self, item_ids: list[float]) -> None:
        if not item_ids:
            logger.warning("No history items selected for merging.")
            return
        try:
            history_data: list[tuple[str, bool, float]] = self.app.monitor.get_history() # type: ignore
            id_to_content: dict[float, str] = {item[2]: item[0] for item in history_data}

            merged_content_parts: list[str] = [id_to_content[item_id] for item_id in item_ids if item_id in id_to_content]

            if merged_content_parts:
                merged_content = "\n".join(merged_content_parts)
                self.app.master.clipboard_clear() # type: ignore
                self.app.master.clipboard_append(merged_content) # type: ignore
                logger.info(f"Copied merged content: {merged_content[:50]}...")
            else:
                logger.warning("No valid history items selected for merging.")
        except Exception as e:
            logger.error(f"Error merging and copying selected history: {e}", exc_info=True)

    def format_selected_item(self) -> None:
        try:
            selected_indices: tuple[int, ...] = self.app.gui.history_component.listbox.curselection() # type: ignore
            if not selected_indices:
                return

            from src.gui.dialogs.format_dialog import FormatDialog

            dialog: FormatDialog = self.app.create_toplevel(FormatDialog, self.app.settings_manager) # type: ignore
            selected_plugin: Plugin | None = dialog.selected_plugin

            if selected_plugin:
                self.apply_plugin_to_selected_item(selected_plugin)

        except IndexError:
            log_and_show_error("エラー", "フォーマット対象の項目が選択されていません。", exc_info=True)
        except Exception as e:
            log_and_show_error("エラー", f"フォーマット中に予期せぬエラーが発生しました。\n\n{e}", exc_info=True)

    def apply_plugin_to_selected_item(self, plugin_instance: Plugin) -> None:
        try:
            history_component: HistoryListComponent = self.app.gui.history_component # type: ignore
            selected_indices: tuple[int, ...] = history_component.listbox.curselection() # type: ignore
            if not selected_indices:
                return

            selected_index: int = selected_indices[0]

            history_data: list[tuple[str, bool, float]] = history_component.history # type: ignore
            if 0 <= selected_index < len(history_data):
                original_text: str = history_data[selected_index][0]
                item_id: float = history_data[selected_index][2] # Get item_id

                processed_text: str = plugin_instance.process(original_text) # type: ignore

                if processed_text != original_text:
                    command = UpdateHistoryCommand(
                        monitor=self.app.monitor, # type: ignore
                        item_id=item_id, # Corrected argument
                        original_text=original_text,
                        new_text=processed_text
                    )
                    self.undo_manager.execute_command(command)
                    logger.info(f"Executed format command for item with ID {item_id} with {plugin_instance.name}")
                else:
                    logger.warning(f"Plugin '{plugin_instance.name}' made no changes.")

        except IndexError:
            log_and_show_error("エラー", "フォーマット対象の項目が選択されていません。", exc_info=True)
        except Exception as e:
            log_and_show_error("エラー", f"プラグインの適用中にエラーが発生しました。\n\n{e}", exc_info=True)

    def handle_search_history(self, search_query: str) -> None:
        if search_query:
            filtered_history: list[tuple[str, bool, float]] = self.app.monitor.get_filtered_history(search_query) # type: ignore
            self.app.gui.update_clipboard_display(self.app.monitor.last_clipboard_data, filtered_history) # type: ignore
        else:
            self.app.gui.update_clipboard_display(self.app.monitor.last_clipboard_data, self.app.monitor.get_history()) # type: ignore
