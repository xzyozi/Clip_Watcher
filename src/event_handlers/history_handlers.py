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
        self.event_dispatcher.subscribe("HISTORY_SEARCH", self.handle_search_history)
        self.event_dispatcher.subscribe("HISTORY_CREATE_QUICK_TASK", self.handle_create_quick_task)
        self.event_dispatcher.subscribe("HISTORY_ITEM_EDITED", self.handle_history_item_edited)
        self.event_dispatcher.subscribe("REQUEST_UNDO_LAST_ACTION", self.undo_last_action)
        self.event_dispatcher.subscribe("REQUEST_REDO_LAST_ACTION", self.redo_last_action)

    def handle_history_item_edited(self, data):
        """Handles the request to update a history item and stores undo state."""
        try:
            selected_indices = self.app.gui.history_listbox.curselection()
            if not selected_indices:
                return
            
            selected_index = selected_indices[0]
            new_text = data['new_text']
            original_text = data['original_text']

            self.app.undo_stack.append({
                'type': 'edit',
                'index': selected_index,
                'original_text': original_text,
                'new_text': new_text
            })
            self.app.redo_stack.clear()

            self.app.monitor.update_history_item(selected_index, new_text)
            self.app.gui.enable_undo_button()
            self.app.gui.disable_redo_button()
            logger.info(f"Updated history item at index {selected_index}.")

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

            from src.gui.format_dialog import FormatDialog
            
            dialog = FormatDialog(self.app.master, self.app, self.app.settings_manager)
            selected_plugin = dialog.selected_plugin

            if selected_plugin:
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
                    self.app.undo_stack.append({
                        'type': 'format',
                        'index': selected_index,
                        'original_text': original_text,
                        'processed_text': processed_text
                    })
                    self.app.redo_stack.clear()
                    
                    self.app.monitor.update_history_item(selected_index, processed_text)
                    self.app.gui.enable_undo_button()
                    self.app.gui.disable_redo_button()
                    logger.info(f"Formatted item at index {selected_index} with {plugin_instance.name}")
                else:
                    logger.warn(f"Plugin '{plugin_instance.name}' made no changes.")

        except IndexError:
            log_and_show_error("エラー", "フォーマット対象の項目が選択されていません。", exc_info=True)
        except Exception as e:
            log_and_show_error("エラー", f"プラグインの適用中にエラーが発生しました。\n\n{e}", exc_info=True)

    def undo_last_action(self):
        """Reverts the last user action (format or edit)."""
        if not self.app.undo_stack:
            logger.warn("No action to undo.")
            return

        try:
            undo_info = self.app.undo_stack.pop()
            action_type = undo_info.get('type')
            index = undo_info['index']
            original_text = undo_info['original_text']
            
            current_text_to_check = undo_info.get('processed_text') if action_type == 'format' else undo_info.get('new_text')

            current_text, _ = self.app.gui.history_data[index]

            if current_text == current_text_to_check:
                self.app.monitor.update_history_item(index, original_text)
                self.app.redo_stack.append(undo_info)
                self.app.gui.enable_redo_button()
                logger.info(f"Undo {action_type} for item at index {index}")
            else:
                # If the text has changed unexpectedly, put the item back on the stack
                self.app.undo_stack.append(undo_info)
                logger.warn("Cannot undo: The item has been modified since the last action.")

        except Exception as e:
            log_and_show_error("エラー", f"元に戻す処理中にエラーが発生しました。\n\n{e}", exc_info=True)
        finally:
            if not self.app.undo_stack:
                self.app.gui.disable_undo_button()

    def redo_last_action(self):
        """Redoes the last undone action."""
        if not self.app.redo_stack:
            logger.warn("No action to redo.")
            return

        try:
            redo_info = self.app.redo_stack.pop()
            action_type = redo_info.get('type')
            index = redo_info['index']
            original_text = redo_info['original_text']
            
            text_to_apply = redo_info.get('processed_text') if action_type == 'format' else redo_info.get('new_text')

            current_text, _ = self.app.gui.history_data[index]

            if current_text == original_text:
                self.app.monitor.update_history_item(index, text_to_apply)
                self.app.undo_stack.append(redo_info)
                self.app.gui.enable_undo_button()
                logger.info(f"Redo {action_type} for item at index {index}")
            else:
                # If the text has changed unexpectedly, put the item back on the stack
                self.app.redo_stack.append(redo_info)
                logger.warn("Cannot redo: The item has been modified since the last action.")

        except Exception as e:
            log_and_show_error("エラー", f"やり直し処理中にエラーが発生しました。\n\n{e}", exc_info=True)
        finally:
            if not self.app.redo_stack:
                self.app.gui.disable_redo_button()

    def handle_search_history(self, search_query):
        self.event_dispatcher.dispatch("REQUEST_SEARCH_HISTORY", search_query)
