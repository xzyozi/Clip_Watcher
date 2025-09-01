import tkinter as tk
import tkinter.messagebox # Import messagebox

# This module will contain functions or a class for event handling

# Example: A function to handle copying selected history
def handle_copy_selected_history(gui_instance, history_data, selected_index):
    try:
        selected_item_content = history_data[selected_index]
        # Use tkinter's clipboard methods
        gui_instance.master.clipboard_clear()
        gui_instance.master.clipboard_append(selected_item_content)
        print(f"Copied from history (Tkinter): {selected_item_content[:50]}...")
    except IndexError:
        pass # No item selected

def handle_quit(monitor_callback, master):
    if monitor_callback:
        monitor_callback()
    master.quit()

def handle_clear_all_history(monitor_instance, gui_instance):
    # Clear history in the monitor
    monitor_instance.clear_history()
    # Update GUI to reflect cleared history
    gui_instance.update_clipboard_display("", []) # Clear current display and history list
    print("All history cleared.")

def handle_delete_selected_history(gui_instance, monitor_instance):
    try:
        selected_indices = gui_instance.history_listbox.curselection()
        if not selected_indices:
            print("No history item selected for deletion.")
            return

        # Get the actual history data from the monitor, not just the displayed text
        # This is important because the displayed text might be truncated.
        # We need to delete from the monitor's internal history list.
        # The selected_indices are based on the displayed listbox, which corresponds
        # to the order in monitor_instance.history.

        # Convert tuple of indices to list and sort in descending order
        # to avoid issues when deleting items from a list while iterating.
        indices_to_delete = sorted(list(selected_indices), reverse=True)

        for index in indices_to_delete:
            monitor_instance.delete_history_item(index)

        # After deletion, update the GUI to reflect the new history
        # The monitor's history has changed, so we need to get the updated history
        # and pass it to the GUI.
        updated_history = monitor_instance.get_history()
        gui_instance.update_clipboard_display(monitor_instance.last_clipboard_data, updated_history)
        print(f"Deleted {len(selected_indices)} selected history item(s).")

    except Exception as e:
        print(f"Error deleting selected history: {e}")

def handle_delete_all_unpinned_history(monitor_instance, gui_instance):
    # Placeholder for future implementation
    print("Delete All Unpinned clicked (functionality not yet implemented).")
    # In a real implementation, this would call a method on monitor_instance
    # to delete unpinned items and then update the GUI.

def handle_copy_fixed_phrase(gui_instance, phrase):
    try:
        gui_instance.master.clipboard_clear()
        gui_instance.master.clipboard_append(phrase)
        print(f"Copied fixed phrase: {phrase[:50]}...")
    except Exception as e:
        print(f"Error copying fixed phrase: {e}")

def handle_always_on_top(master, always_on_top_var):
    # Toggle the always on top attribute of the master window
    master.attributes('-topmost', always_on_top_var.get())
    print(f"Always on Top set to: {always_on_top_var.get()}")

def handle_about():
    tkinter.messagebox.showinfo(
        "バージョン情報 (About)",
        "ClipWatcher\nバージョン: 0.1.0\n開発者: Gemini CLI Agent\n\nこのアプリケーションは、クリップボードの履歴を管理し、再利用を容易にするために開発されました。"
    )