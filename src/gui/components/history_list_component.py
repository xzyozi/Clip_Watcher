from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.bootstrap.base_application import BaseApplication
    from src.gui.base.context_menu import HistoryContextMenu


class HistoryListComponent(tk.Frame):
    """履歴一覧を表示するGUIコンポーネント。

    Requirements 5.1, 5.2: 内部ウィジェット属性 `self.tree`（`ttk.Treeview`）は
    History_Caller（`src/gui/main_gui.py` の `ClipWatcherGUI`、`src/gui/menu_bar.py`、
    `src/event_handlers/history_handlers.py` の `HistoryEventHandlers`）に対しては
    公開しない。History_Caller は選択状態・item_idの取得に `get_selected_indices()` /
    `get_ids_for_indices()` / `get_selected_ids()` のみを使用すること。

    例外として `src/gui/base/context_menu.py` の `HistoryContextMenu._get_tree()` は、
    右クリック位置の行特定（`identify_row()`）・単一選択化・フォーカス設定のために
    `self.tree` へ直接アクセスする設計上意図された唯一の経路である
    （`.kiro/specs/treeview-migration/design.md` の Component 1/2 を参照）。
    `HistoryContextMenu` は Glossary 上の History_Caller の定義に含まれない。
    """

    def __init__(self, master: tk.Misc, app_instance: BaseApplication) -> None:
        super().__init__(master)
        self.app = app_instance
        self.displayed_history: list[tuple[str, bool, float]] = []  # Will store the full (content, is_pinned, timestamp) tuples
        self.current_theme: dict[str, str] = {}
        self._updating_history: bool = False

        self._create_widgets()
        self._bind_events()

    def _create_widgets(self) -> None:
        # Requirements 5.2: self.tree は History_Caller に対して公開しない内部実装詳細である。
        # 唯一の許容された外部参照元は HistoryContextMenu._get_tree()（context_menu.py）のみ。
        self.tree = ttk.Treeview(self, show="tree", selectmode="extended")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.config(yscrollcommand=self.scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _bind_events(self) -> None:
        self.tree.bind("<<TreeviewSelect>>", self._on_history_select)
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        from src.gui.base import context_menu
        history_context_menu: HistoryContextMenu = context_menu.HistoryContextMenu(self.master, self.app) # type: ignore
        self.tree.bind("<Button-3>", history_context_menu.show)

    def _on_double_click(self, event: tk.Event) -> None:
        """Handler for double-click events to copy an item."""
        selected_indices: tuple[int, ...] = self.get_selected_indices()
        if not selected_indices:
            return

        # On double-click, we typically act on the first selected item.
        item_ids: list[float] = self.get_ids_for_indices(selected_indices[:1])
        if item_ids:
            # The event now passes a list of IDs, even if it's just one.
            self.app.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", item_ids) # type: ignore

    def _on_history_select(self, event: tk.Event) -> None:
        # Requirements 10.1: update_history() の実行中（self._updating_history が True の間）は
        # 選択変更イベントの通知処理を抑制し、ここで早期returnする。
        if self._updating_history:
            return
        # This event is now handled by the parent (main_gui) to update the text widget
        self.app.event_dispatcher.dispatch("HISTORY_SELECTION_CHANGED", { # type: ignore
            "selected_indices": self.get_selected_indices()
        })

    def get_selected_indices(self) -> tuple[int, ...]:
        """現在選択中の表示行を表示順インデックス（0始まり）の昇順タプルで返す。選択が0件の場合は空タプルを返す。"""
        return tuple(sorted(self.tree.index(iid) for iid in self.tree.selection()))

    def get_ids_for_indices(self, indices: Sequence[int]) -> list[float]:
        """表示順インデックスのシーケンスを対応する履歴item IDのリストに変換する。

        `displayed_history` の範囲外のインデックス（負値・上限超過）は結果から除外される。
        `displayed_history` が空の場合は、渡された `indices` の値に関わらず常に空リストを返す。
        """
        return [self.displayed_history[i][2] for i in indices if 0 <= i < len(self.displayed_history)]

    def _iid_for_item_id(self, item_id: float) -> str:
        """履歴item ID（float、一意なタイムスタンプ）からTreeview iid文字列を生成する。"""
        return f"item-{item_id!r}"

    def _format_display_text(self, content: str, index: int) -> str:
        """表示行のテキストを生成する。

        改行・キャリッジリターンを除去した内容の先頭100文字に "..." を付与し、
        表示順インデックス（1始まりの番号）を先頭に付与する。
        ピン留めの装飾は背景色タグ（"pinned"）で行うため、ここでは付与しない。
        """
        display_text = content.replace('\n', ' ').replace('\r', '')
        return f"{index + 1}. {display_text[:100]}..."

    def update_history(self, history: list[tuple[str, bool, float]], theme: dict[str, str]) -> None:
        """履歴データとテーマの内容に基づき、表示ウィジェットの内容を差分更新する。

        Preconditions:
            - history はタプル (content, is_pinned, item_id) のリストであり、item_id は履歴全体で一意
            - theme は 'pinned_bg' キーを持つ dict[str, str]

        Postconditions:
            - history と theme が直前の表示内容（displayed_history, current_theme）と完全に一致する場合、
              表示内容の再構築を行わずウィジェット状態を不変のまま早期returnする（Requirements 2.1）
            - 更新後、Treeview上の表示行の集合は history の各要素の item_id から導出される iid の集合と一致する
            - 更新後の表示行の並び順は history の順序と一致する（Requirements 2.4）
            - 更新後の表示行の件数は len(history) と一致する（Requirements 2.5）
            - 更新前に選択されていた行のうち、更新後も存在する行のみ選択状態が復元される
            - self._updating_history は処理完了後に必ず False に戻る（例外発生時も finally で保証、Requirements 10.2）
            - 更新処理の実行中（self._updating_history が True の間）は選択変更イベントの通知処理が抑制される（Requirements 10.1）
        """
        # 履歴データとテーマが両方完全に同一の場合は何もしない（スクロールと選択状態を100%保護）
        if self.displayed_history == history and self.current_theme == theme:
            return  # 事後条件: ウィジェット状態は不変

        # Requirements 10.3: 抑制機構（self._updating_history）の有効化に失敗した場合、
        # 有効化されるまで更新処理本体を開始してはならない。
        # self._updating_history はこのクラスの通常の bool 属性であり、`__slots__` や
        # プロパティsetterでの検証も存在しないため、代入自体が例外を投げることはない
        # （＝有効化は常に成功する）。したがって次行の代入が完了する前に
        # 更新処理本体（try節）が実行されることはなく、要件10.3は成立する。
        self._updating_history = True
        try:
            # Requirements 10.1: この try 節の実行中は self._updating_history が True のままであり、
            # _on_history_select() 側のガードにより選択変更イベントの通知処理が抑制される。
            # Requirements 3.1-3.3: 更新前の選択状態を保存する（生存行のみ復元するための基準値）
            prev_selection: tuple[str, ...] = self.tree.selection()
            # Requirements 3.4: 更新前のスクロール位置（fraction）を保存する
            scroll_pos: tuple[float, float] = self.tree.yview()

            self.displayed_history = history
            self.current_theme = theme
            pinned_bg_color = theme["pinned_bg"]

            new_iids: list[str] = [self._iid_for_item_id(item[2]) for item in history]
            new_iid_set: set[str] = set(new_iids)
            existing_iid_set: set[str] = set(self.tree.get_children(""))

            # 1. 不要になった行を削除（更新後に存在しなくなった表示行のみを削除する: Requirements 2.2）
            stale_iids = existing_iid_set - new_iid_set
            if stale_iids:
                self.tree.delete(*stale_iids)

            # 2. 表示順に挿入・更新・移動
            #    既存行は delete/insert せず item()+move() で内容更新する（Requirements 2.3）
            for index, (content, is_pinned, _item_id) in enumerate(history):
                iid = new_iids[index]
                display_text = self._format_display_text(content, index)
                # Requirements 7.1: is_pinned が True の行には "pinned" タグを付与する。
                # Requirements 7.2: is_pinned が False の行には空タプル（タグなし）とし、
                #   "pinned" タグを付与しない。
                tags: tuple[str, ...] = ("pinned",) if is_pinned else ()

                if iid in existing_iid_set:
                    self.tree.item(iid, text=display_text, tags=tags)
                    self.tree.move(iid, "", index)
                else:
                    self.tree.insert("", index, iid=iid, text=display_text, tags=tags)

            # Requirements 7.3: "pinned" タグの背景色は theme["pinned_bg"]（pinned_bg_color）から
            # 取得する。tag_configure は既存・新規行を問わず全ての "pinned" タグ付き行に一括適用される。
            self.tree.tag_configure("pinned", background=pinned_bg_color)

            # 3. 選択・スクロール状態の復元
            # Requirements 3.1, 3.2: 更新前に選択されていた行のうち、更新後も存在する（tree.exists）行のみを
            # 選択状態に復元する。存在しない行は restored_selection から自動的に除外される。
            restored_selection = tuple(iid for iid in prev_selection if self.tree.exists(iid))
            # Requirements 3.3: 更新前が空選択（prev_selection == ()）の場合、restored_selection も
            # 空タプルになり、この if は False となるため selection_set() は呼ばれず、更新後も選択0件のままになる。
            # （selection_set() を空タプルで呼び出すと環境によって tk.TclError になる可能性があるため、
            #   このガードは要件3.3の実現だけでなく安全性の観点でも必須）
            if restored_selection:
                self.tree.selection_set(restored_selection)
            # Requirements 3.4: 更新前のスクロール位置に復元する
            self.tree.yview_moveto(scroll_pos[0])
        finally:
            # Requirements 10.2: 更新処理が正常終了した場合・try節内で例外が発生した場合の
            # いずれでも、finally ブロックにより更新中フラグの解除が確実に実行される。
            # Requirements 8.3: この finally はフラグ解除のみを行い、tree / displayed_history /
            # current_theme を切替前の状態へ巻き戻す処理は含まない。try節内で例外が発生した場合、
            # ピン留め表示行（"pinned" タグ）を含む更新済みの状態はロールバックされず失敗時点のまま
            # 残り、例外はこの finally を抜けた後にそのまま呼び出し元へ伝播する。
            self._updating_history = False

    def apply_theme(self, theme: dict[str, str]) -> None:
        """テーマ切替時にウィジェットへ新しいテーマを適用する。

        Requirements 8.2: History_Tree（self.tree）本体の背景色・文字色・選択色は
        `ThemeManager.apply_theme()`（src/gui/theme_manager.py）側で
        `ttk.Style().configure('Treeview', ...)` / `style.map('Treeview', ...)` として
        グローバルに設定される。`ttk.Treeview` インスタンスは個別に `bg`/`fg` 等の
        ウィジェット単位設定を持たないため、このメソッドでは Treeview 本体への
        config() 呼び出しは行わず、スタイル設定は ThemeManager 側に一本化する。

        Requirements 8.1: テーマが切り替わるとき、現在表示中の履歴データ
        （self.displayed_history）に対してピン留め背景色タグ（"pinned"）を
        再適用する。

        実現方法: update_history() を `history=self.displayed_history`（変更なし）・
        `theme=新テーマ` で再呼び出しする。update_history() 冒頭の早期return判定は
        `self.displayed_history == history and self.current_theme == theme` の
        両方が真の場合のみ成立するため、テーマが変化していれば
        `self.current_theme != theme` となり早期returnされず、
        "pinned" タグの再構築（tag_configure 含む）が必ず実行される
        （displayed_history 自体が変化していないケースでも同様に成立する）。

        Requirements 8.3: このメソッド自体にも、呼び出し先の update_history() にも、
        切替前のピン留め表示行の状態を保存して例外発生時に復元するようなtry/except処理は
        存在しない。テーマ切替処理中に例外が発生した場合は、既存の例外伝播（呼び出し元への
        素通し）に委ね、ピン留め表示行の状態は失敗時点のままとする。
        """
        # Requirements 8.1: displayed_history はそのままに新テーマを渡して再呼び出しする。
        # update_history() 側で theme != self.current_theme と判定され、
        # "pinned" タグが現在表示中の履歴データに対して再適用される。
        self.update_history(self.displayed_history, theme) # Re-apply pinned colors

    def apply_font(self, font: tk.font.Font) -> None:
        """フォント変更をTreeviewへ適用する。

        Requirements 1.1: History_List_Component は内部の表示ウィジェットとして
        `ttk.Treeview` のインスタンスを常にちょうど1つ保持する。`ttk.Treeview` は
        `tk.Listbox` と異なり `font` 等のウィジェット単位設定を持たず、ttkスタイル
        （`ttk.Style`）経由でのみ見た目を制御できるため、`self.tree.config(font=...)`
        ではなく `ttk.Style` の "Treeview" スタイルにフォントを設定する。
        """
        style = ttk.Style(self)
        style.configure("Treeview", font=font)
