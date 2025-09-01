import tkinter as tk
from src.event_handlers import main_handlers as event_handlers

def create_menu_bar(master, app_instance):
    menubar = tk.Menu(master)

    # File Menu
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="設定 (Settings)...", command=lambda: print("Settings clicked"))
    file_menu.add_command(label="履歴をエクスポート (Export History)...", command=lambda: print("Export History clicked"))
    file_menu.add_command(label="履歴をインポート (Import History)...", command=lambda: print("Import History clicked"))
    file_menu.add_separator()

    # Fixed Phrases Sub-menu
    fixed_phrases_menu = tk.Menu(file_menu, tearoff=0)
    fixed_phrases_menu.add_command(label="挨拶 (Greeting)", command=lambda: event_handlers.handle_copy_fixed_phrase(app_instance.gui, "いつもお世話になっております。"))
    fixed_phrases_menu.add_command(label="署名 (Signature)", command=lambda: event_handlers.handle_copy_fixed_phrase(app_instance.gui, "よろしくお願いいたします.\n\n[あなたの名前]\n[あなたの会社]"))
    fixed_phrases_menu.add_command(label="電話番号 (Phone Number)", command=lambda: event_handlers.handle_copy_fixed_phrase(app_instance.gui, "090-XXXX-XXXX"))
    file_menu.add_cascade(label="定型文 (Fixed Phrases)", menu=fixed_phrases_menu)
    file_menu.add_separator()

    file_menu.add_command(label="終了 (Exit)", command=lambda: event_handlers.handle_quit(app_instance.monitor.stop, master))
    menubar.add_cascade(label="ファイル (File)", menu=file_menu)

    # Edit Menu
    edit_menu = tk.Menu(menubar, tearoff=0)
    edit_menu.add_command(label="検索 (Find)...", command=lambda: print("Find clicked"))
    edit_menu.add_command(label="選択項目を結合してコピー (Copy Selected as Merged)", command=lambda: print("Copy Selected as Merged clicked"))
    edit_menu.add_separator()
    edit_menu.add_command(label="選択項目を削除 (Delete Selected)", command=lambda: event_handlers.handle_delete_selected_history(app_instance.gui, app_instance.monitor))
    edit_menu.add_command(label="ピン留め以外をすべて削除 (Delete All Unpinned)", command=lambda: print("Delete All Unpinned clicked"))
    edit_menu.add_command(label="すべての履歴を削除 (Clear All History)", command=lambda: event_handlers.handle_clear_all_history(app_instance.monitor, app_instance.gui))
    menubar.add_cascade(label="編集 (Edit)", menu=edit_menu)

    # View Menu
    view_menu = tk.Menu(menubar, tearoff=0)
    # Variable to hold the state of the "Always on Top" checkbutton
    app_instance.always_on_top_var = tk.BooleanVar(value=False) # Initialize to False
    view_menu.add_checkbutton(label="常に手前に表示 (Always on Top)",
                              command=lambda: event_handlers.handle_always_on_top(master, app_instance.always_on_top_var),
                              variable=app_instance.always_on_top_var)
    
    theme_menu = tk.Menu(view_menu, tearoff=0)
    theme_menu.add_command(label="ライト (Light)", command=lambda: print("Light theme clicked"))
    theme_menu.add_command(label="ダーク (Dark)", command=lambda: print("Dark theme clicked"))
    theme_menu.add_command(label="システム設定に合わせる (Follow System)", command=lambda: print("Follow System theme clicked"))
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
    help_menu.add_command(label="使い方 (How to Use)", command=lambda: print("How to Use clicked"))
    help_menu.add_command(label="バージョン情報 (About)", command=lambda: print("About clicked"))
    menubar.add_cascade(label="ヘルプ (Help)", menu=help_menu)

    return menubar