import tkinter as tk
from src.event_handlers import main_handlers as event_handlers

def create_history_context_menu(master, gui_instance, monitor_instance):
    context_menu = tk.Menu(master, tearoff=0)

    context_menu.add_command(label="選択項目をコピー (Copy Selected)", 
                             command=lambda: event_handlers.handle_copy_selected_history(gui_instance, gui_instance.history_data, gui_instance.history_listbox.curselection()[0]))
    context_menu.add_command(label="選択項目を削除 (Delete Selected)", 
                             command=lambda: event_handlers.handle_delete_selected_history(gui_instance, monitor_instance))
    context_menu.add_separator()

    # Dynamically set Pin/Unpin label
    selected_index = None
    try:
        selected_index = gui_instance.history_listbox.curselection()[0]
        # Get the actual item from the monitor's history based on the displayed order
        item_tuple = monitor_instance.get_history()[selected_index]
        is_pinned = item_tuple[1] # is_pinned is the second element of the tuple
        pin_unpin_label = "ピン解除 (Unpin)" if is_pinned else "ピン留め (Pin)"
    except IndexError:
        pin_unpin_label = "ピン留め/ピン解除 (Pin/Unpin)" # Default if no item selected

    context_menu.add_command(label=pin_unpin_label, 
                             command=lambda: event_handlers.handle_pin_unpin_history(gui_instance, monitor_instance))
    
    return context_menu

def show_history_context_menu(event, gui_instance, monitor_instance):
    # Select the item under the cursor
    try:
        gui_instance.history_listbox.selection_clear(0, tk.END)
        gui_instance.history_listbox.selection_set(gui_instance.history_listbox.nearest(event.y))
        gui_instance.history_listbox.activate(gui_instance.history_listbox.nearest(event.y))
    except:
        pass # No item under cursor

    context_menu = create_history_context_menu(gui_instance.master, gui_instance, monitor_instance)
    context_menu.tk_popup(event.x_root, event.y_root)

def create_text_widget_context_menu(master, text_widget):
    context_menu = tk.Menu(master, tearoff=0)

    context_menu.add_command(label="切り取り (Cut)", command=lambda: text_widget.event_generate("<<Cut>>"))
    context_menu.add_command(label="コピー (Copy)", command=lambda: text_widget.event_generate("<<Copy>>"))
    context_menu.add_command(label="貼り付け (Paste)", command=lambda: text_widget.event_generate("<<Paste>>"))
    context_menu.add_separator()
    context_menu.add_command(label="すべて選択 (Select All)", command=lambda: text_widget.tag_add(tk.SEL, "1.0", tk.END))

    return context_menu

def show_text_widget_context_menu(event, text_widget):
    context_menu = create_text_widget_context_menu(text_widget, text_widget)
    context_menu.tk_popup(event.x_root, event.y_root)
