import tkinter as tk
from tkinter import messagebox, ttk
from ..custom_widgets import CustomEntry, CustomText
from ..base_toplevel_gui import BaseToplevelGUI

class PhraseEditDialog(BaseToplevelGUI):
    """
    定型文の追加または編集を行うためのダイアログ。
    CustomEntryとCustomTextを使用し、右クリックメニューをサポートします。
    """
    def __init__(self, master, app_instance, phrase_manager, phrase_key=None):
        super().__init__(master, app_instance)
        self.transient(master)
        self.grab_set()

        self.phrase_manager = phrase_manager
        self.original_phrase = phrase_key # The key is the phrase itself
        self.result = None

        if phrase_key:
            self.title("定型文の編集 (Edit Phrase)")
        else:
            self.title("新しい定型文の追加 (Add New Phrase)")

        # --- Widgets ---

        # Value Text
        tk.Label(self, text="内容 (Content):").grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        self.value_text = CustomText(self, width=50, height=10)
        self.value_text.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        if self.original_phrase:
            self.value_text.insert("1.0", self.original_phrase)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Buttons
        buttons_container = ttk.Frame(self)
        buttons_container.grid(row=1, column=1, pady=10, sticky="e")

        save_button = ttk.Button(buttons_container, text="保存 (Save)", command=self.save_phrase)
        save_button.pack(side="left", padx=5)

        cancel_button = ttk.Button(buttons_container, text="キャンセル (Cancel)", command=self.destroy)
        cancel_button.pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(self)

    def save_phrase(self):
        new_phrase = self.value_text.get("1.0", tk.END).strip()

        if not new_phrase:
            messagebox.showerror("エラー (Error)", "内容は必須です。\n(Content cannot be empty.)", parent=self)
            return

        try:
            if self.original_phrase:  # Edit mode
                if self.original_phrase != new_phrase:
                    if not self.phrase_manager.update_phrase(self.original_phrase, new_phrase):
                        messagebox.showerror("エラー (Error)", "その内容は既に存在するか、更新に失敗しました。\n(The content may already exist or the update failed.)", parent=self)
                        return
            else:  # Add mode
                if not self.phrase_manager.add_phrase(new_phrase):
                    messagebox.showerror("エラー (Error)", "その内容は既に存在します。\n(The content already exists.)", parent=self)
                    return
            
            self.result = True
            self.destroy()
        except Exception as e:
            messagebox.showerror("エラー (Error)", f"予期せぬエラーが発生しました: {e}", parent=self)
            self.destroy()