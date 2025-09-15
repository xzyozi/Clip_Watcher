import tkinter as tk
from src.event_handlers import main_handlers as event_handlers

def create_menu_bar(master, app_instance):
    menubar = tk.Menu(master)

    # File Menu
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="設定 (Settings)...", command=app_instance.open_settings_window)
    file_menu.add_command(label="履歴をエクスポート (Export History)...", command=app_instance.file_handlers.handle_export_history)
    file_menu.add_command(label="履歴をインポート (Import History)...", command=app_instance.file_handlers.handle_import_history)
    file_menu.add_separator()

    file_menu.add_command(label="終了 (Exit)", command=app_instance.file_handlers.handle_quit)
    menubar.add_cascade(label="ファイル (File)", menu=file_menu)

    # Edit Menu
    edit_menu = tk.Menu(menubar, tearoff=0)
    edit_menu.add_command(label="検索 (Find)...", command=lambda: print("Find clicked"))
    edit_menu.add_command(label="選択項目を結合してコピー (Copy Selected as Merged)", command=lambda: app_instance.event_dispatcher.dispatch("HISTORY_COPY_MERGED", app_instance.gui.history_listbox.curselection()))
    edit_menu.add_separator()
    edit_menu.add_command(label="選択項目を削除 (Delete Selected)", command=app_instance.history_handlers.handle_delete_selected_history)
    edit_menu.add_command(label="ピン留め以外をすべて削除 (Delete All Unpinned)", command=app_instance.history_handlers.handle_delete_all_unpinned_history)
    edit_menu.add_command(label="すべての履歴を削除 (Clear All History)", command=app_instance.history_handlers.handle_clear_all_history)
    menubar.add_cascade(label="編集 (Edit)", menu=edit_menu)

    # View Menu
    view_menu = tk.Menu(menubar, tearoff=0)
    # Variable to hold the state of the "Always on Top" checkbutton
    app_instance.always_on_top_var = tk.BooleanVar(value=app_instance.settings_manager.get_setting("always_on_top"))
    view_menu.add_checkbutton(label="常に手前に表示 (Always on Top)",
                              command=lambda: app_instance.event_dispatcher.dispatch("SETTINGS_ALWAYS_ON_TOP", app_instance.always_on_top_var.get()),
                              variable=app_instance.always_on_top_var)
    
    # Theme Menu
    app_instance.theme_var = tk.StringVar(value=app_instance.settings_manager.get_setting("theme"))
    theme_menu = tk.Menu(view_menu, tearoff=0)
    theme_menu.add_radiobutton(label="ライト (Light)", variable=app_instance.theme_var, value="light",
                               command=lambda: app_instance.settings_handlers.handle_set_theme("light"))
    theme_menu.add_radiobutton(label="ダーク (Dark)", variable=app_instance.theme_var, value="dark",
                               command=lambda: app_instance.settings_handlers.handle_set_theme("dark"))
    # "Follow System" is more complex, will just print for now
    theme_menu.add_radiobutton(label="システム設定に合わせる (Follow System)", variable=app_instance.theme_var, value="system",
                               command=lambda: print("Follow System theme clicked (not yet implemented)"))
    view_menu.add_cascade(label="テーマ (Theme)", menu=theme_menu)
    
    view_menu.add_separator()
    
    filter_menu = tk.Menu(view_menu, tearoff=0)
    filter_menu.add_command(label="すべて表示 (Show All)", command=lambda: print("Show All clicked"))
    filter_menu.add_command(label="テキストのみ (Show Text Only)", command=lambda: print("Show Text Only clicked"))
    filter_menu.add_command(label="画像のみ (Show Images Only)", command=lambda: print("Show Images Only clicked"))
    view_menu.add_cascade(label="表示内容のフィルタ (Filter)", menu=filter_menu)
    
    menubar.add_cascade(label="表示 (View)", menu=view_menu)

    # Help Menu
    help_menu = tk.Menu(menubar, tearoff=0)
    help_menu.add_command(label="使い方 (How to Use)", command=event_handlers.handle_how_to_use)
    help_menu.add_command(label="バージョン情報 (About)", command=event_handlers.handle_about)
    menubar.add_cascade(label="ヘルプ (Help)", menu=help_menu)

    return menubar