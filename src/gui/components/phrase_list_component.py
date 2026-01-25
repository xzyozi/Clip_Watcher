from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, cast

from src.core.exceptions import PhraseError
from src.gui.base import context_menu
from src.gui.base.base_frame_gui import BaseFrameGUI

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication
    from src.gui.base.context_menu import PhraseListContextMenu
    from src.gui.components.phrase_edit_component import PhraseEditComponent


class PhraseListComponent(BaseFrameGUI):
    """定型文リスト表示コンポーネント"""

    def __init__(self, master: tk.Misc, app_instance: BaseApplication) -> None:
        super().__init__(master, app_instance)
        self.logger = logging.getLogger(__name__)
        self.edit_component: PhraseEditComponent | None = None  # Will be set later
        self._create_widgets()
        self._populate_listbox()
        self._bind_events()

    def set_edit_component(self, edit_component: PhraseEditComponent) -> None:
        self.edit_component = edit_component
        self._bind_context_menu()

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
        if self.edit_component:
            phrase_context_menu: PhraseListContextMenu = context_menu.PhraseListContextMenu(self.master, self.app, self, self.edit_component) # type: ignore
            self.phrase_listbox.bind("<Button-3>", phrase_context_menu.show)

    def _populate_listbox(self) -> None:
        """リストボックスに定型文を表示"""
        self.phrase_listbox.delete(0, tk.END)
        for phrase in self.app.fixed_phrases_manager.get_phrases(): # type: ignore
            self.phrase_listbox.insert(tk.END, phrase)

    def _copy_selected_phrase(self) -> None:
        """選択された定型文をクリップボードにコピー"""
        try:
            selected_index = self.phrase_listbox.curselection()[0]
            selected_phrase: str = cast(str, self.phrase_listbox.get(selected_index))

            if not selected_phrase:
                raise PhraseError("空の定型文はコピーできません")

            self.master.clipboard_clear() # type: ignore
            self.master.clipboard_append(selected_phrase) # type: ignore

            self.logger.info(f"定型文をコピーしました: {selected_phrase[:20]}...")
            messagebox.showinfo("コピー完了", "定型文をクリップボードにコピーしました。", parent=self) # type: ignore

        except IndexError:
            self.logger.warning("定型文が選択されていません")
            messagebox.showwarning("警告", "定型文を選択してください。", parent=self) # type: ignore
        except PhraseError as e:
            self.log_and_show_error("エラー",f"定型文コピーエラー: {str(e)}")
        except Exception as e:
            self.log_and_show_error("エラー",f"予期せぬエラー: {str(e)}", exc_info=True)

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
