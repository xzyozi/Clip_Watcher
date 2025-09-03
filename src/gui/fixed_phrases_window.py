import tkinter as tk
from tkinter import simpledialog, messagebox

class FixedPhrasesWindow(tk.Toplevel):
    def __init__(self, master, fixed_phrases_manager):
        super().__init__(master)
        self.title("定型文の管理 (Manage Fixed Phrases)")
        self.geometry("400x300")
        self.fixed_phrases_manager = fixed_phrases_manager

        self._create_widgets()
        self._populate_listbox()

    def _create_widgets(self):
        # Listbox for phrases
        self.phrase_listbox = tk.Listbox(self, height=10)
        self.phrase_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=5)

        self.add_button = tk.Button(button_frame, text="追加 (Add)", command=self._add_phrase)
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.edit_button = tk.Button(button_frame, text="編集 (Edit)", command=self._edit_phrase)
        self.edit_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = tk.Button(button_frame, text="削除 (Delete)", command=self._delete_phrase)
        self.delete_button.pack(side=tk.LEFT, padx=5)

    def _populate_listbox(self):
        self.phrase_listbox.delete(0, tk.END)
        for phrase in self.fixed_phrases_manager.get_phrases():
            self.phrase_listbox.insert(tk.END, phrase)

    def _add_phrase(self):
        new_phrase = simpledialog.askstring("定型文の追加", "新しい定型文を入力してください:", parent=self)
        if new_phrase:
            if self.fixed_phrases_manager.add_phrase(new_phrase):
                self._populate_listbox()
            else:
                messagebox.showwarning("警告", "その定型文は既に存在します。", parent=self)

    def _edit_phrase(self):
        try:
            selected_index = self.phrase_listbox.curselection()[0]
            old_phrase = self.phrase_listbox.get(selected_index)
            edited_phrase = simpledialog.askstring("定型文の編集", "定型文を編集してください:", initialvalue=old_phrase, parent=self)
            if edited_phrase:
                if self.fixed_phrases_manager.update_phrase(old_phrase, edited_phrase):
                    self._populate_listbox()
                else:
                    messagebox.showwarning("警告", "その定型文は既に存在するか、変更がありません。", parent=self)
        except IndexError:
            messagebox.showwarning("警告", "編集する定型文を選択してください。", parent=self)

    def _delete_phrase(self):
        try:
            selected_index = self.phrase_listbox.curselection()[0]
            phrase_to_delete = self.phrase_listbox.get(selected_index)
            if messagebox.askyesno("確認", f"'{phrase_to_delete}' を削除しますか？", parent=self):
                if self.fixed_phrases_manager.delete_phrase(phrase_to_delete):
                    self._populate_listbox()
        except IndexError:
            messagebox.showwarning("警告", "削除する定型文を選択してください。", parent=self)
