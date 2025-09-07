import tkinter as tk

def create_history_context_menu(master, app_instance):
    context_menu = tk.Menu(master, tearoff=0)

    context_menu.add_command(label="選択項目をコピー (Copy Selected)", 
                             command=app_instance.history_handlers.handle_copy_selected_history)
    context_menu.add_command(label="選択項目を削除 (Delete Selected)", 
                             command=app_instance.history_handlers.handle_delete_selected_history)
    context_menu.add_separator()

    # Dynamically set Pin/Unpin label
    selected_index = None
    try:
        selected_index = app_instance.gui.history_listbox.curselection()[0]
        item_tuple = app_instance.monitor.get_history()[selected_index]
        is_pinned = item_tuple[1]
        pin_unpin_label = "ピン解除 (Unpin)" if is_pinned else "ピン留め (Pin)"
    except IndexError:
        pin_unpin_label = "ピン留め/ピン解除 (Pin/Unpin)"

    context_menu.add_command(label=pin_unpin_label, 
                             command=app_instance.history_handlers.handle_pin_unpin_history)
    
    return context_menu

def show_history_context_menu(event, app_instance):
    try:
        app_instance.gui.history_listbox.selection_clear(0, tk.END)
        app_instance.gui.history_listbox.selection_set(app_instance.gui.history_listbox.nearest(event.y))
        app_instance.gui.history_listbox.activate(app_instance.gui.history_listbox.nearest(event.y))
    except:
        pass

    context_menu = create_history_context_menu(app_instance.master, app_instance)
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