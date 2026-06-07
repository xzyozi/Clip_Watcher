from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, cast, Callable, Any

from reusable_gui.base.base_frame_gui import BaseFrameGUI

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from reusable_gui.core.bootstrap.base_application import BaseApplication
    from reusable_gui.base.context_menu import PhraseListContextMenu


class PhraseListComponent(BaseFrameGUI):
    """定型文リスト表示コンポーネント (汎用版)"""

    def __init__(self, master: tk.Misc, app_instance: BaseApplication) -> None:
        super().__init__(master, app_instance)
        self.logger = logging.getLogger(__name__)
        
        # Callbacks for decoupling
        self.get_phrases_cb: Callable[[], list[str]] = lambda: []
        self.copy_cb: Callable[[str], None] = self._default_copy_cb
        self.add_cb: Callable[[], None] = lambda: None
        self.edit_cb: Callable[[], None] = lambda: None
        self.delete_cb: Callable[[], None] = lambda: None
        self.error_handler_cb: Callable[[str, Exception], None] = lambda msg, e: self.log_and_show_error("エラー", f"{msg}: {str(e)}")

        self._create_widgets()
        self._populate_listbox()
        self._bind_events()

    def set_callbacks(
        self,
        get_phrases: Callable[[], list[str]],
        copy: Callable[[str], None] | None = None,
        add: Callable[[], None] | None = None,
        edit: Callable[[], None] | None = None,
        delete: Callable[[], None] | None = None,
        error_handler: Callable[[str, Exception], None] | None = None
    ) -> None:
        """Sets callbacks to decouple this component from concrete application logic."""
        self.get_phrases_cb = get_phrases
        if copy:
            self.copy_cb = copy
        if add:
            self.add_cb = add
        if edit:
            self.edit_cb = edit
        if delete:
            self.delete_cb = delete
        if error_handler:
            self.error_handler_cb = error_handler
            
        self._bind_context_menu()
        self._populate_listbox()

    def _create_widgets(self) -> None:
        # リストボックスの作成
        self.phrase_listbox = tk.Listbox(self, height=10)
        self.phrase_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # スクロールバーの追加
        scrollbar = tk.Scrollbar(self)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # リストボックスとスクロールバーの連携
        self.phrase_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.phrase_listbox.yview)

    def _bind_events(self) -> None:
        # ダブルクリックでコピー機能を設定
        self.phrase_listbox.bind('<Double-Button-1>', lambda e: self._copy_selected_phrase())

    def _bind_context_menu(self) -> None:
        from reusable_gui.base import context_menu
        phrase_context_menu: PhraseListContextMenu = context_menu.PhraseListContextMenu(
            self.master,
            self.app,
            self.phrase_listbox,
            copy_cb=self._copy_selected_phrase,
            add_cb=self.add_cb,
            edit_cb=self.edit_cb,
            delete_cb=self.delete_cb
        )
        self.phrase_listbox.bind("<Button-3>", phrase_context_menu.show)

    def _populate_listbox(self) -> None:
        """リストボックスに定型文を表示"""
        self.phrase_listbox.delete(0, tk.END)
        for phrase in self.get_phrases_cb():
            self.phrase_listbox.insert(tk.END, phrase)

    def _default_copy_cb(self, selected_phrase: str) -> None:
        """Default fallback copying logic."""
        self.master.clipboard_clear()  # type: ignore
        self.master.clipboard_append(selected_phrase)  # type: ignore
        self.logger.info(f"定型文をコピーしました: {selected_phrase[:20]}...")
        messagebox.showinfo("コピー完了", "定型文をクリップボードにコピーしました。", parent=self)  # type: ignore

    def _copy_selected_phrase(self) -> None:
        """選択された定型文をクリップボードにコピー"""
        try:
            selected_index = self.phrase_listbox.curselection()[0]
            selected_phrase: str = cast(str, self.phrase_listbox.get(selected_index))

            if not selected_phrase:
                raise ValueError("空の定型文はコピーできません")

            self.copy_cb(selected_phrase)

        except IndexError:
            self.logger.warning("定型文が選択されていません")
            messagebox.showwarning("警告", "定型文を選択してください。", parent=self)  # type: ignore
        except Exception as e:
            self.error_handler_cb("定型文コピーエラー", e)

    def get_selected_phrase(self) -> str | None:
        """選択された定型文を返す"""
        try:
            selected_index = self.phrase_listbox.curselection()[0]
            return cast(str, self.phrase_listbox.get(selected_index))
        except IndexError:
            return None

    def refresh(self) -> None:
        """リストの表示を更新"""
        self._populate_listbox()
