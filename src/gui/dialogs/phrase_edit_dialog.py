from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any

from src.gui.base.base_toplevel_gui import BaseToplevelGUI
from src.gui.custom_widgets import CustomText

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication
    from src.core.fixed_phrases_manager import FixedPhrasesManager


class PhraseEditDialog(BaseToplevelGUI):
    """
    A dialog for adding or editing a fixed phrase.
    """
    def __init__(self, master: tk.Misc, app_instance: BaseApplication, phrase_manager: FixedPhrasesManager, phrase_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(master, app_instance, **kwargs)
        self.transient(master) # type: ignore
        self.grab_set()

        self.phrase_manager = phrase_manager
        self.old_phrase = phrase_key
        self.result = False # Success status

        if self.old_phrase:
            self.title("定型文の編集")
        else:
            self.title("定型文の追加")

        self.geometry("450x250")

        self._create_widgets()

        master.wait_window(self)

    def _create_widgets(self) -> None:
        container = ttk.Frame(self, padding=10)
        container.pack(fill=tk.BOTH, expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        # Content
        content_label = ttk.Label(container, text="内容 (Content):")
        content_label.grid(row=0, column=0, pady=(0, 5), sticky="nw")

        text_frame = ttk.Frame(container)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        self.content_text = CustomText(text_frame, height=8, app=self.app)
        self.content_text.grid(row=0, column=0, sticky="nsew")
        if self.old_phrase:
            self.content_text.insert("1.0", self.old_phrase)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.content_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.content_text.config(yscrollcommand=scrollbar.set)

        # Buttons
        button_frame = ttk.Frame(container)
        button_frame.grid(row=2, column=0, pady=(10, 0), sticky="e")

        save_button = ttk.Button(button_frame, text="保存 (Save)", command=self._on_save)
        save_button.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_button = ttk.Button(button_frame, text="キャンセル (Cancel)", command=self.destroy)
        cancel_button.pack(side=tk.RIGHT)

    def _on_save(self) -> None:
        new_phrase = self.content_text.get("1.0", tk.END).strip()
        if not new_phrase:
            messagebox.showwarning("入力エラー", "内容を入力してください。", parent=self)
            return

        try:
            if self.old_phrase: # Editing existing phrase
                if self.old_phrase != new_phrase:
                    success = self.phrase_manager.update_phrase(self.old_phrase, new_phrase)
                    if not success:
                        messagebox.showerror("エラー", "定型文の更新に失敗しました。\n同じ内容が既に存在する可能性があります。", parent=self)
                        return
            else: # Adding new phrase
                success = self.phrase_manager.add_phrase(new_phrase)
                if not success:
                    messagebox.showerror("エラー", "定型文の追加に失敗しました。\n同じ内容が既に存在する可能性があります。", parent=self)
                    return

            self.result = True
            self.destroy()

        except Exception as e:
            messagebox.showerror("エラー", f"保存中にエラーが発生しました: {e}", parent=self)
