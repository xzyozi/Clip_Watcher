import tkinter as tk
from tkinter import messagebox, simpledialog
import logging
from pathlib import Path
from src.exceptions import PhraseError
from src.gui.components.phrase_list_component import PhraseListComponent
from src.gui.components.phrase_edit_component import PhraseEditComponent

logger = logging.getLogger(__name__)

class FixedPhrasesFrame(tk.Frame):
    """定型文管理フレーム"""
    
    def __init__(self, master, fixed_phrases_manager):
        super().__init__(master)
        self.fixed_phrases_manager = fixed_phrases_manager
        self.logger = logging.getLogger(__name__)
        self._create_widgets()

    def _create_widgets(self):
        """コンポーネントの初期化と配置"""
        try:
            # componentsディレクトリが存在しない場合は作成
            components_dir = Path(__file__).parent / 'components'
            components_dir.mkdir(exist_ok=True)
            
            # リストコンポーネントの作成と配置
            self.list_component = PhraseListComponent(self, self.fixed_phrases_manager)
            self.list_component.pack(fill=tk.BOTH, expand=True)

            # 編集コンポーネントの作成と配置
            self.edit_component = PhraseEditComponent(
                self, 
                self.fixed_phrases_manager, 
                self.list_component
            )
            self.edit_component.pack(fill=tk.X)
            
            self.logger.info("定型文管理フレームを初期化しました")
            
        except Exception as e:
            self.logger.error(f"定型文管理フレームの初期化中にエラー: {str(e)}", exc_info=True)
            raise

    # 他のメソッドはすべてPhraseListComponentとPhraseEditComponentに移動しました