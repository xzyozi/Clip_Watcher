import tkinter as tk
from tkinter import messagebox, simpledialog
import logging
from src.exceptions import PhraseError

logger = logging.getLogger(__name__)

from src.gui.base_frame_gui import BaseFrameGUI

logger = logging.getLogger(__name__)

class PhraseEditComponent(BaseFrameGUI):
    """定型文編集コンポーネント"""
    
    def __init__(self, master, list_component, app_instance):
        super().__init__(master, app_instance)
        self.list_component = list_component
        self.logger = logging.getLogger(__name__)
        self._create_widgets()

    def _create_widgets(self):
        button_frame = tk.Frame(self)
        button_frame.pack(pady=5)

        # コピーボタン
        self.copy_button = tk.Button(button_frame, text="コピー (Copy)", command=self._copy_phrase)
        self.copy_button.pack(side=tk.LEFT, padx=5)

        # 追加ボタン
        self.add_button = tk.Button(button_frame, text="追加 (Add)", command=self._add_phrase)
        self.add_button.pack(side=tk.LEFT, padx=5)

        # 編集ボタン
        self.edit_button = tk.Button(button_frame, text="編集 (Edit)", command=self._edit_phrase)
        self.edit_button.pack(side=tk.LEFT, padx=5)

        # 削除ボタン
        self.delete_button = tk.Button(button_frame, text="削除 (Delete)", command=self._delete_phrase)
        self.delete_button.pack(side=tk.LEFT, padx=5)

    def _copy_phrase(self):
        """選択された定型文をクリップボードにコピー"""
        self.list_component._copy_selected_phrase()

    def _add_phrase(self):
        """新しい定型文を追加"""
        try:
            new_phrase = simpledialog.askstring("定型文の追加", "新しい定型文を入力してください:", parent=self)
            if not new_phrase:  # ユーザーがキャンセルした場合
                return

            if not new_phrase.strip():
                raise PhraseError("空の定型文は追加できません")

            if self.app.fixed_phrases_manager.add_phrase(new_phrase):
                self.logger.info(f"新しい定型文を追加しました: {new_phrase[:20]}...")
                self.list_component.refresh()  # リストを更新
            else:
                raise PhraseError("その定型文は既に存在します")

        except PhraseError as e:
            self.logger.warning(f"定型文追加エラー: {str(e)}")
            messagebox.showwarning("警告", str(e), parent=self)
        except Exception as e:
            self.log_and_show_error("エラー",f"予期せぬエラー: {str(e)}", exc_info=True)

    def _edit_phrase(self):
        """選択された定型文を編集"""
        try:
            old_phrase = self.list_component.get_selected_phrase()
            if not old_phrase:
                raise PhraseError("編集する定型文を選択してください")

            edited_phrase = simpledialog.askstring(
                "定型文の編集", 
                "定型文を編集してください:", 
                initialvalue=old_phrase,
                parent=self
            )
            
            if edited_phrase:
                if self.app.fixed_phrases_manager.update_phrase(old_phrase, edited_phrase):
                    self.logger.info(f"定型文を更新しました: {edited_phrase[:20]}...")
                    self.list_component.refresh()
                else:
                    raise PhraseError("更新に失敗しました")

        except PhraseError as e:
            self.logger.warning(f"定型文編集エラー: {str(e)}")
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
                    self.logger.info(f"定型文を削除しました: {phrase_to_delete[:20]}...")
                    self.list_component.refresh()
                else:
                    raise PhraseError("削除に失敗しました")

        except PhraseError as e:
            self.logger.warning(f"定型文削除エラー: {str(e)}")
            messagebox.showwarning("警告", str(e), parent=self)
        except Exception as e:
            self.log_and_show_error("エラー",f"予期せぬエラー: {str(e)}", exc_info=True)
