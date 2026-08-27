from __future__ import annotations

import logging
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any, cast

from src.db.dto import CategoryDTO, MetaPhraseDTO
from src.gui.base.base_frame_gui import BaseFrameGUI
from src.gui.base.base_toplevel_gui import BaseToplevelGUI
from src.gui.custom_widgets import CustomEntry, CustomText
from src.utils.error_handler import log_and_show_error

if TYPE_CHECKING:
    from src.core.app_main import MainApplication
    from src.core.bootstrap.base_application import BaseApplication

logger = logging.getLogger(__name__)


class CategoryEditDialog(BaseToplevelGUI):
    """カテゴリ作成/編集用のダイアログ"""

    def __init__(
        self,
        parent: tk.Widget,
        app_instance: BaseApplication,
        category_dto: CategoryDTO | None = None,
    ) -> None:
        super().__init__(parent, app_instance)
        self.app: MainApplication = cast("MainApplication", app_instance)  # type: ignore
        self.category_dto = category_dto
        self.result: str | None = None

        self.title(
            self.app.translator("edit_category" if category_dto else "add_category")
        )
        self.geometry("300x120")
        self.resizable(False, False)
        self.grab_set()

        # レイアウト
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=self.app.translator("category_name_label")).pack(
            anchor=tk.W, pady=(0, 5)
        )
        self.entry = CustomEntry(main_frame, app=self.app)
        self.entry.pack(fill=tk.X, pady=(0, 10))

        if self.category_dto:
            self.entry.insert(0, self.category_dto.name)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        self.ok_btn = ttk.Button(btn_frame, text="OK", command=self.on_ok)
        self.ok_btn.pack(side=tk.RIGHT, padx=5)

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        self.cancel_btn.pack(side=tk.RIGHT)

        self.entry.focus_set()

    def on_ok(self) -> None:
        try:
            name = self.entry.get().strip()
            if not name:
                messagebox.showerror(
                    "Error", "Category name cannot be empty.", parent=self
                )
                return

            # 重複チェック
            categories = self.app.db_manager.category_dao.get_all()
            for cat in categories:
                if cat.name.lower() == name.lower():
                    # 編集時で自分自身と同じ名前ならパス
                    if self.category_dto and self.category_dto.id == cat.id:
                        continue
                    messagebox.showerror(
                        "Error", "Category name already exists.", parent=self
                    )
                    return

            self.result = name
            self.destroy()
        except Exception as e:
            log_and_show_error(
                "エラー",
                f"カテゴリ登録処理中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )


class MetaPhraseEditDialog(BaseToplevelGUI):
    """メタ定型文作成/編集用のダイアログ"""

    def __init__(
        self,
        parent: tk.Widget,
        app_instance: BaseApplication,
        phrase_dto: MetaPhraseDTO | None = None,
        default_category_id: int | None = None,
    ) -> None:
        super().__init__(parent, app_instance)
        self.app: MainApplication = cast("MainApplication", app_instance)  # type: ignore
        self.phrase_dto = phrase_dto
        self.result: tuple[str, str, int] | None = None

        self.title(self.app.translator("edit_phrase" if phrase_dto else "add_phrase"))
        self.geometry("450x350")
        self.grab_set()

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # タイトル入力
        ttk.Label(main_frame, text=self.app.translator("phrase_title_label")).pack(
            anchor=tk.W, pady=(0, 2)
        )
        self.title_entry = CustomEntry(main_frame, app=self.app)
        self.title_entry.pack(fill=tk.X, pady=(0, 10))

        # カテゴリ選択
        ttk.Label(main_frame, text=self.app.translator("meta_category_title")).pack(
            anchor=tk.W, pady=(0, 2)
        )
        self.cat_combobox = ttk.Combobox(main_frame, state="readonly")
        self.cat_combobox.pack(fill=tk.X, pady=(0, 10))

        # カテゴリリストのロード
        self.categories = self.app.db_manager.category_dao.get_all()
        self.cat_names = [cat.name for cat in self.categories]
        self.cat_combobox["values"] = self.cat_names

        # 初期値セット
        if self.phrase_dto:
            self.title_entry.insert(0, self.phrase_dto.title)
            # 現在のカテゴリを選択
            for idx, cat in enumerate(self.categories):
                if cat.id == self.phrase_dto.category_id:
                    self.cat_combobox.current(idx)
                    break
        elif default_category_id is not None:
            for idx, cat in enumerate(self.categories):
                if cat.id == default_category_id:
                    self.cat_combobox.current(idx)
                    break
        elif self.cat_names:
            self.cat_combobox.current(0)

        # 内容入力
        ttk.Label(main_frame, text=self.app.translator("phrase_content_label")).pack(
            anchor=tk.W, pady=(0, 2)
        )
        self.content_text = CustomText(main_frame, height=8, wrap=tk.WORD, app=self.app)
        self.content_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        if self.phrase_dto:
            self.content_text.insert("1.0", self.phrase_dto.content)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        self.ok_btn = ttk.Button(btn_frame, text="OK", command=self.on_ok)
        self.ok_btn.pack(side=tk.RIGHT, padx=5)

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        self.cancel_btn.pack(side=tk.RIGHT)

        self.title_entry.focus_set()

    def on_ok(self) -> None:
        try:
            title = self.title_entry.get().strip()
            content = self.content_text.get("1.0", "end-1c").strip()
            cat_index = self.cat_combobox.current()

            if not content:
                messagebox.showerror("Error", "Content cannot be empty.", parent=self)
                return
            if cat_index == -1:
                messagebox.showerror("Error", "Please select a category.", parent=self)
                return

            category_id = self.categories[cat_index].id
            if category_id is None:
                return

            self.result = (title, content, category_id)
            self.destroy()
        except Exception as e:
            log_and_show_error(
                "エラー",
                f"定型文登録処理中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )


class MetaManagementFrame(BaseFrameGUI):
    """メタ管理タブのメインフレーム"""

    def __init__(self, parent: tk.Widget, app_instance: BaseApplication) -> None:
        super().__init__(parent, app_instance)
        self.logger = logging.getLogger(__name__)
        self.app: MainApplication = cast("MainApplication", app_instance)  # type: ignore
        self.category_list: list[CategoryDTO] = []
        self.phrase_list: list[MetaPhraseDTO] = []
        self.selected_category_id: int | None = None  # None means All

        self._create_widgets()
        self.refresh_categories()

        self.app.event_dispatcher.subscribe(
            "LANGUAGE_CHANGED", self.on_language_changed
        )

    def _create_widgets(self) -> None:
        try:
            # 左右分割 PanedWindow
            self.paned_window = tk.PanedWindow(
                self,
                orient=tk.HORIZONTAL,
                sashrelief=tk.RAISED,
                bg=self.app.theme_manager.get_bg_color()
                if hasattr(self.app.theme_manager, "get_bg_color")
                else "#f0f0f0",
            )
            self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # ================= 左側：カテゴリ管理 =================
            self.left_frame = ttk.Frame(self.paned_window, padding="5")
            self.paned_window.add(self.left_frame, width=180)

            self.category_label = ttk.Label(
                self.left_frame,
                text=self.app.translator("meta_category_title"),
                font=("", 10, "bold"),
            )
            self.category_label.pack(anchor=tk.W, pady=(0, 5))

            # カテゴリ一覧リストボックス（美観向上のためのスタイル設定）
            self.cat_listbox = tk.Listbox(
                self.left_frame,
                selectmode=tk.SINGLE,
                exportselection=False,
                activestyle="none",
            )
            self.cat_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
            self.cat_listbox.bind("<<ListboxSelect>>", self.on_category_select)

            # 右クリックコンテキストメニュー
            self.cat_menu = tk.Menu(self, tearoff=0)
            self.cat_menu.add_command(
                label=self.app.translator("add_category"), command=self.add_category
            )
            self.cat_menu.add_command(
                label=self.app.translator("edit_category"), command=self.edit_category
            )
            # プラットフォームに応じた右クリックのバインド (macOSはButton-2, Windows/LinuxはButton-3)
            if sys.platform == "darwin":
                self.cat_listbox.bind("<Button-2>", self.show_context_menu)
            else:
                self.cat_listbox.bind("<Button-3>", self.show_context_menu)

            # カテゴリボタン群
            cat_btn_frame = ttk.Frame(self.left_frame)
            cat_btn_frame.pack(fill=tk.X)

            self.add_cat_btn = ttk.Button(
                cat_btn_frame,
                text=self.app.translator("add"),
                command=self.add_category,
                width=6,
            )
            self.add_cat_btn.pack(side=tk.LEFT, padx=1, fill=tk.X, expand=True)

            self.edit_cat_btn = ttk.Button(
                cat_btn_frame,
                text=self.app.translator("edit"),
                command=self.edit_category,
                width=6,
            )
            self.edit_cat_btn.pack(side=tk.LEFT, padx=1, fill=tk.X, expand=True)

            self.del_cat_btn = ttk.Button(
                cat_btn_frame,
                text=self.app.translator("delete"),
                command=self.delete_category,
                width=6,
            )
            self.del_cat_btn.pack(side=tk.LEFT, padx=1, fill=tk.X, expand=True)

            # ================= 右側：定型文管理 =================
            self.right_frame = ttk.Frame(self.paned_window, padding="5")
            self.paned_window.add(self.right_frame, width=320)

            self.phrase_label = ttk.Label(
                self.right_frame,
                text=self.app.translator("meta_phrase_title"),
                font=("", 10, "bold"),
            )
            self.phrase_label.pack(anchor=tk.W, pady=(0, 5))

            # 定型文一覧 Treeview
            tree_scroll = ttk.Scrollbar(self.right_frame, orient="vertical")
            tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            self.phrase_tree = ttk.Treeview(
                self.right_frame,
                columns=("title", "content"),
                show="headings",
                yscrollcommand=tree_scroll.set,
            )
            self.phrase_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
            tree_scroll.config(command=self.phrase_tree.yview)

            # ヘッダー設定（ヘッダーとデータのアライメントを左揃えで統一）
            self.phrase_tree.heading(
                "title", text=self.app.translator("phrase_title_label"), anchor=tk.W
            )
            self.phrase_tree.heading(
                "content", text=self.app.translator("phrase_content_label"), anchor=tk.W
            )
            self.phrase_tree.column("title", width=100, anchor=tk.W)
            self.phrase_tree.column("content", width=220, anchor=tk.W)

            self.phrase_tree.bind("<Double-1>", self.on_phrase_double_click)

            # 定型文ボタン群
            phrase_btn_frame = ttk.Frame(self.right_frame)
            phrase_btn_frame.pack(fill=tk.X)

            self.copy_phrase_btn = ttk.Button(
                phrase_btn_frame,
                text=self.app.translator("copy"),
                command=self.copy_selected_phrase,
            )
            self.copy_phrase_btn.pack(side=tk.LEFT, padx=2)

            self.add_phrase_btn = ttk.Button(
                phrase_btn_frame,
                text=self.app.translator("add"),
                command=self.add_phrase,
            )
            self.add_phrase_btn.pack(side=tk.LEFT, padx=2)

            self.edit_phrase_btn = ttk.Button(
                phrase_btn_frame,
                text=self.app.translator("edit"),
                command=self.edit_phrase,
            )
            self.edit_phrase_btn.pack(side=tk.LEFT, padx=2)

            self.del_phrase_btn = ttk.Button(
                phrase_btn_frame,
                text=self.app.translator("delete"),
                command=self.delete_phrase,
            )
            self.del_phrase_btn.pack(side=tk.LEFT, padx=2)

            self.logger.info("メタ定型文管理フレームを初期化しました")
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"メタ定型文管理フレームの初期化中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )
            raise

    def refresh_categories(self) -> None:
        """データベースからカテゴリ一覧を取得し、リストボックスを更新します。"""
        try:
            self.cat_listbox.delete(0, tk.END)

            # すべて特殊項目を追加（左側余白として半角スペースを追加）
            all_text = self.app.translator("all_categories")
            self.cat_listbox.insert(tk.END, f"  {all_text}")

            self.category_list = self.app.db_manager.category_dao.get_all()
            for cat in self.category_list:
                self.cat_listbox.insert(tk.END, f"  {cat.name}")

            # 選択状態を復元
            if self.selected_category_id is None:
                self.cat_listbox.selection_set(0)
            else:
                found = False
                for idx, cat in enumerate(self.category_list):
                    if cat.id == self.selected_category_id:
                        self.cat_listbox.selection_set(idx + 1)
                        found = True
                        break
                if not found:
                    self.selected_category_id = None
                    self.cat_listbox.selection_set(0)

            self.refresh_phrases()
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"カテゴリ一覧の更新中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    def refresh_phrases(self) -> None:
        """現在選択されているカテゴリに属する定型文を表示します。"""
        try:
            for item in self.phrase_tree.get_children():
                self.phrase_tree.delete(item)

            self.phrase_list = self.app.db_manager.meta_phrase_dao.get_by_category(
                self.selected_category_id
            )
            for phrase in self.phrase_list:
                # プレビュー表示用
                preview_content = phrase.content.replace("\n", " ")
                display_title = (
                    phrase.title
                    if phrase.title.strip()
                    else self.app.translator("no_title")
                )
                self.phrase_tree.insert(
                    "",
                    tk.END,
                    iid=str(phrase.id),
                    values=(display_title, preview_content),
                )
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"定型文一覧の更新中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    def on_category_select(self, event: tk.Event | None = None) -> None:
        try:
            selection = self.cat_listbox.curselection()
            if not selection:
                return

            idx = selection[0]
            if idx == 0:
                self.selected_category_id = None
            else:
                self.selected_category_id = self.category_list[idx - 1].id

            self.refresh_phrases()
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"カテゴリ選択処理中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    # ================= カテゴリ操作 =================
    def add_category(self) -> None:
        try:
            dialog = CategoryEditDialog(self, self.app)
            self.wait_window(dialog)
            if dialog.result:
                dto = CategoryDTO(name=dialog.result)
                new_id = self.app.db_manager.category_dao.add(dto)
                if new_id != -1:
                    self.logger.info(
                        "カテゴリ '%s' (ID: %d) を追加しました", dialog.result, new_id
                    )
                self.refresh_categories()
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"カテゴリの追加中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    def edit_category(self) -> None:
        try:
            selection = self.cat_listbox.curselection()
            if not selection or selection[0] == 0:
                return

            idx = selection[0]
            target_cat = self.category_list[idx - 1]

            dialog = CategoryEditDialog(self, self.app, target_cat)
            self.wait_window(dialog)
            if dialog.result:
                old_name = target_cat.name
                target_cat.name = dialog.result
                if self.app.db_manager.category_dao.update(target_cat):
                    self.logger.info(
                        "カテゴリ '%s' を '%s' に変更しました (ID: %s)",
                        old_name,
                        dialog.result,
                        target_cat.id,
                    )
                self.refresh_categories()
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"カテゴリの変更中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    def delete_category(self) -> None:
        try:
            selection = self.cat_listbox.curselection()
            if not selection or selection[0] == 0:
                return

            idx = selection[0]
            target_cat = self.category_list[idx - 1]
            cat_id = target_cat.id
            if cat_id is None:
                return

            # セーフガード: カテゴリ内の定型文件数チェック
            phrase_count = self.app.db_manager.category_dao.get_meta_phrase_count(
                cat_id
            )
            if phrase_count > 0:
                msg = self.app.translator("confirm_category_delete_msg").format(
                    count=phrase_count
                )
                confirm = messagebox.askyesno(
                    self.app.translator("confirm_category_delete_title"),
                    msg,
                    parent=self,
                )
                if not confirm:
                    return

            if self.app.db_manager.category_dao.delete(cat_id):
                self.logger.info(
                    "カテゴリ '%s' (ID: %d) を削除しました", target_cat.name, cat_id
                )
            self.selected_category_id = None
            self.refresh_categories()
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"カテゴリの削除中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    # ================= 定型文操作 =================
    def copy_selected_phrase(self) -> None:
        try:
            selected = self.phrase_tree.selection()
            if not selected:
                return

            phrase_id = int(selected[0])
            for phrase in self.phrase_list:
                if phrase.id == phrase_id:
                    # システムクリップボードへコピー (履歴の最上位に移動＆通知表示)
                    self.app.monitor.update_clipboard(phrase.content)
                    self.logger.info(
                        "メタ定型文 '%s' (ID: %d) をクリップボードにコピーしました",
                        phrase.title,
                        phrase_id,
                    )
                    break
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"定型文のコピー中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    def on_phrase_double_click(self, event: tk.Event) -> None:
        self.copy_selected_phrase()

    def add_phrase(self) -> None:
        try:
            if not self.category_list:
                messagebox.showerror(
                    "Error", "Please create at least one category first.", parent=self
                )
                return

            dialog = MetaPhraseEditDialog(
                self, self.app, default_category_id=self.selected_category_id
            )
            self.wait_window(dialog)
            if dialog.result:
                title, content, category_id = dialog.result
                dto = MetaPhraseDTO(
                    title=title,
                    content=content,
                    category_id=category_id,
                    created_at=time.time(),
                )
                new_id = self.app.db_manager.meta_phrase_dao.add(dto)
                if new_id != -1:
                    self.logger.info(
                        "メタ定型文 '%s' (ID: %d) を追加しました", title, new_id
                    )
                self.refresh_phrases()
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"定型文の追加中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    def edit_phrase(self) -> None:
        try:
            selected = self.phrase_tree.selection()
            if not selected:
                return

            phrase_id = int(selected[0])
            target_phrase: MetaPhraseDTO | None = None
            for phrase in self.phrase_list:
                if phrase.id == phrase_id:
                    target_phrase = phrase
                    break

            if not target_phrase:
                return

            dialog = MetaPhraseEditDialog(self, self.app, target_phrase)
            self.wait_window(dialog)
            if dialog.result:
                title, content, category_id = dialog.result
                target_phrase.title = title
                target_phrase.content = content
                target_phrase.category_id = category_id
                if self.app.db_manager.meta_phrase_dao.update(target_phrase):
                    self.logger.info(
                        "メタ定型文 '%s' (ID: %d) を更新しました", title, phrase_id
                    )
                self.refresh_phrases()
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"定型文の変更中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    def delete_phrase(self) -> None:
        try:
            selected = self.phrase_tree.selection()
            if not selected:
                return

            phrase_id = int(selected[0])
            target_phrase: MetaPhraseDTO | None = None
            for phrase in self.phrase_list:
                if phrase.id == phrase_id:
                    target_phrase = phrase
                    break

            if self.app.db_manager.meta_phrase_dao.delete(phrase_id):
                title = target_phrase.title if target_phrase else str(phrase_id)
                self.logger.info(
                    "メタ定型文 '%s' (ID: %d) を削除しました", title, phrase_id
                )
            self.refresh_phrases()
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"定型文の削除中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    def show_context_menu(self, event: tk.Event) -> None:
        """右クリック時にコンテキストメニューを表示します。"""
        try:
            clicked_idx = self.cat_listbox.nearest(event.y)

            # 項目がある場合のみ処理（無効な位置を右クリックした場合は選択を変えない）
            bbox = self.cat_listbox.bbox(clicked_idx)
            if bbox and event.y <= bbox[1] + bbox[3]:
                self.cat_listbox.selection_clear(0, tk.END)
                self.cat_listbox.selection_set(clicked_idx)
                self.cat_listbox.activate(clicked_idx)
                self.on_category_select()  # 定型文リストの更新をトリガー

                # [すべて] (インデックス0) では編集・削除を無効化
                if clicked_idx == 0:
                    self.cat_menu.entryconfig(1, state="disabled")
                    self.cat_menu.entryconfig(2, state="disabled")
                else:
                    self.cat_menu.entryconfig(1, state="normal")
                    self.cat_menu.entryconfig(2, state="normal")
            else:
                # 項目外をクリックした場合は追加のみ有効
                self.cat_menu.entryconfig(1, state="disabled")
                self.cat_menu.entryconfig(2, state="disabled")

            self.cat_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"コンテキストメニュー表示中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )

    # ================= 多言語対応 =================
    def on_language_changed(self, event: Any = None) -> None:
        try:
            self.category_label.config(text=self.app.translator("meta_category_title"))
            self.add_cat_btn.config(text=self.app.translator("add"))
            self.edit_cat_btn.config(text=self.app.translator("edit"))
            self.del_cat_btn.config(text=self.app.translator("delete"))

            # コンテキストメニューの再翻訳
            self.cat_menu.entryconfig(0, label=self.app.translator("add_category"))
            self.cat_menu.entryconfig(1, label=self.app.translator("edit_category"))
            self.cat_menu.entryconfig(2, label=self.app.translator("delete_category"))

            self.phrase_label.config(text=self.app.translator("meta_phrase_title"))
            self.phrase_tree.heading(
                "title", text=self.app.translator("phrase_title_label")
            )
            self.phrase_tree.heading(
                "content", text=self.app.translator("phrase_content_label")
            )

            self.copy_phrase_btn.config(text=self.app.translator("copy"))
            self.add_phrase_btn.config(text=self.app.translator("add"))
            self.edit_phrase_btn.config(text=self.app.translator("edit"))
            self.del_phrase_btn.config(text=self.app.translator("delete"))

            self.refresh_categories()
        except Exception as e:
            self.log_and_show_error(
                "エラー",
                f"言語の切り替え処理中にエラーが発生しました: {str(e)}",
                exc_info=True,
            )
