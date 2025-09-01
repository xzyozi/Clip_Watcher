import tkinter as tk

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
