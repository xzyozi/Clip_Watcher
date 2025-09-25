import tkinter as tk

def create_history_context_menu(master, app_instance):
    context_menu = tk.Menu(master, tearoff=0)

    has_selection = False
    selected_index = None
    try:
        selected_index = app_instance.gui.history_listbox.curselection()[0]
        has_selection = True
    except IndexError:
        pass

    context_menu.add_command(label="選択項目をコピー (Copy Selected)", 
                             command=lambda: app_instance.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", app_instance.gui.history_listbox.curselection()))
    
    context_menu.add_command(label="クイックタスクとして開く (Open as Quick Task)",
                             command=lambda: app_instance.event_dispatcher.dispatch("HISTORY_CREATE_QUICK_TASK", app_instance.gui.history_listbox.curselection()),
                             state="normal" if has_selection else "disabled")
    
    format_state = "normal" if has_selection else "disabled"
    context_menu.add_command(label="フォーマット (Format)",
                             command=app_instance.history_handlers.format_selected_item,
                             state=format_state)

    context_menu.add_command(label="選択項目を削除 (Delete Selected)", 
                             command=lambda: app_instance.event_dispatcher.dispatch("HISTORY_DELETE_SELECTED", app_instance.gui.history_listbox.curselection()))
    
    context_menu.add_separator()

    # Undo command
    undo_state = "normal" if app_instance.last_formatted_info else "disabled"
    context_menu.add_command(label="フォーマットを元に戻す (Undo Format)",
                             command=app_instance.history_handlers.undo_last_format,
                             state=undo_state)

    context_menu.add_separator()

    # Pin/Unpin logic
    pin_unpin_label = "ピン留め/ピン解除 (Pin/Unpin)"
    pin_unpin_state = "disabled"
    if has_selection:
        item_tuple = app_instance.monitor.get_history()[selected_index]
        is_pinned = item_tuple[1]
        pin_unpin_label = "ピン解除 (Unpin)" if is_pinned else "ピン留め (Pin)"
        pin_unpin_state = "normal"

    context_menu.add_command(label=pin_unpin_label, 
                             command=lambda: app_instance.event_dispatcher.dispatch("HISTORY_PIN_UNPIN", selected_index),
                             state=pin_unpin_state)
    
    return context_menu

def show_history_context_menu(event, app_instance):
    try:
        # Select the item under the cursor before showing the menu
        app_instance.gui.history_listbox.selection_clear(0, tk.END)
        item_index = app_instance.gui.history_listbox.nearest(event.y)
        app_instance.gui.history_listbox.selection_set(item_index)
        app_instance.gui.history_listbox.activate(item_index)
    except tk.TclError:
        # This can happen if the listbox is empty
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