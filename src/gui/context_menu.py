import tkinter as tk
from src.event_handlers import main_handlers as event_handlers

def create_history_context_menu(master, gui_instance, monitor_instance):
    context_menu = tk.Menu(master, tearoff=0)

    context_menu.add_command(label="選択項目をコピー (Copy Selected)", 
                             command=lambda: event_handlers.handle_copy_selected_history(gui_instance, gui_instance.history_data, gui_instance.history_listbox.curselection()[0]))
    context_menu.add_command(label="選択項目を削除 (Delete Selected)", 
                             command=lambda: event_handlers.handle_delete_selected_history(gui_instance, monitor_instance))
    context_menu.add_separator()
    context_menu.add_command(label="ピン留め/ピン解除 (Pin/Unpin)", 
                             command=lambda: print("Pin/Unpin clicked from context menu"))
    
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
