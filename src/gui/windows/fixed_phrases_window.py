from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING

from src.gui.base.base_frame_gui import BaseFrameGUI
from src.gui.components import PhraseEditComponent, PhraseListComponent

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication


class FixedPhrasesFrame(BaseFrameGUI):
    """定型文管理フレーム"""

    def __init__(self, master: tk.Misc, app_instance: BaseApplication) -> None:
        super().__init__(master, app_instance)
        self.logger = logging.getLogger(__name__)
        self._create_widgets()

    def _create_widgets(self) -> None:
        """コンポーネントの初期化と配置"""
        try:
            # componentsディレクトリが存在しない場合は作成
            components_dir = Path(__file__).parent / 'components'
            components_dir.mkdir(exist_ok=True)

            # リストコンポーネントの作成と配置
            self.list_component = PhraseListComponent(self, self.app)
            self.list_component.pack(fill=tk.BOTH, expand=True)

            # 編集コンポーネントの作成と配置
            self.edit_component = PhraseEditComponent(
                self,
                self.list_component,
                self.app
            )
            self.edit_component.pack(fill=tk.X)

            # 編集コンポーネントをリストコンポーネントに設定
            self.list_component.set_edit_component(self.edit_component)

            self.logger.info("定型文管理フレームを初期化しました")

        except Exception as e:
            self.log_and_show_error("エラー",f"定型文管理フレームの初期化中にエラー: {str(e)}", exc_info=True)
            raise

    # 他のメソッドはすべてPhraseListComponentとPhraseEditComponentに移動しました
