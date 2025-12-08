import tkinter as tk
from tkinter import ttk, messagebox
import logging

from src.core.exceptions import PhraseError
from src.gui.base.base_frame_gui import BaseFrameGUI
from src.gui.dialogs.phrase_edit_dialog import PhraseEditDialog

logger = logging.getLogger(__name__)

class PhraseEditComponent(BaseFrameGUI):
    """定型文編集コンポーネント"""
    
    def __init__(self, master, list_component, app_instance):
        super().__init__(master, app_instance)
        self.list_component = list_component
        self._create_widgets()

    def _create_widgets(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=5)

        # コピーボタン
        self.copy_button = ttk.Button(button_frame, text="コピー (Copy)", command=self._copy_phrase)
        self.copy_button.pack(side=tk.LEFT, padx=5)

        # 追加ボタン
        self.add_button = ttk.Button(button_frame, text="追加 (Add)", command=self._add_phrase)
        self.add_button.pack(side=tk.LEFT, padx=5)

        # 編集ボタン
        self.edit_button = ttk.Button(button_frame, text="編集 (Edit)", command=self._edit_phrase)
        self.edit_button.pack(side=tk.LEFT, padx=5)

        # 削除ボタン
        self.delete_button = ttk.Button(button_frame, text="削除 (Delete)", command=self._delete_phrase)
        self.delete_button.pack(side=tk.LEFT, padx=5)

    def _copy_phrase(self):
        """選択された定型文をクリップボードにコピー"""
        self.list_component._copy_selected_phrase()

    def _add_phrase(self):
        """新しい定型文を追加"""
        try:
            dialog = PhraseEditDialog(
                self,
                app_instance=self.app,
                phrase_manager=self.app.fixed_phrases_manager
            )
            if dialog.result:
                logger.info("新しい定型文を追加しました。")
                self.list_component.refresh()

        except Exception as e:
            self.log_and_show_error("エラー", f"予期せぬエラー: {str(e)}", exc_info=True)

    def _edit_phrase(self):
        """選択された定型文を編集"""
        try:
            old_phrase = self.list_component.get_selected_phrase()
            if not old_phrase:
                raise PhraseError("編集する定型文を選択してください")

            dialog = PhraseEditDialog(
                self,
                app_instance=self.app,
                phrase_manager=self.app.fixed_phrases_manager,
                phrase_key=old_phrase
            )
            
            if dialog.result:
                logger.info(f"定型文を更新しました。")
                self.list_component.refresh()

        except PhraseError as e:
            logger.warning(f"定型文編集エラー: {str(e)}")
            messagebox.showwarning("警告", str(e), parent=self)
        except Exception as e:
            self.log_and_show_error("エラー",f"予期せぬエラー: {str(e)}", exc_info=True)

    def _delete_phrase(self):
        """選択された定型文を削除"""
        try:
            phrase_to_delete = self.list_component.get_selected_phrase()
            if not phrase_to_delete:
                raise PhraseError("削除する定型文を選択してください")

            if messagebox.askyesno("確認", f"'{phrase_to_delete}' を削除しますか？", parent=self):
                if self.app.fixed_phrases_manager.delete_phrase(phrase_to_delete):
                    logger.info(f"定型文を削除しました: {phrase_to_delete[:20]}...")
                    self.list_component.refresh()
                else:
                    raise PhraseError("削除に失敗しました")

        except PhraseError as e:
            logger.warning(f"定型文削除エラー: {str(e)}")
            messagebox.showwarning("警告", str(e), parent=self)
        except Exception as e:
            self.log_and_show_error("エラー",f"予期せぬエラー: {str(e)}", exc_info=True)
