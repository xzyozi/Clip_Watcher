from __future__ import annotations

import sys
import tkinter as tk
from collections.abc import Mapping, Sequence
from tkinter import ttk
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.core.bootstrap.base_application import BaseApplication
    from src.gui.base.context_menu import HistoryContextMenu

_DRAG_SCROLL_INTERVAL_MS = 60
_SHIFT_MASK = 0x0001
_CTRL_MASK = 0x0004
_DARWIN_CMD_MASK = 0x0008


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

    current_font: tk.font.Font | None = None

    def __init__(self, master: tk.Misc, app_instance: BaseApplication) -> None:
        super().__init__(master)
        self.app = app_instance
        self.displayed_history: list[
            tuple[str, bool, float]
        ] = []  # Will store the full (content, is_pinned, timestamp) tuples
        self.displayed_hotkey_bindings: dict[int, str] = {}
        self.current_theme: dict[str, str] = {}
        # 最後に行へ反映した IconManager のキャッシュ世代（Issue #203）
        self._displayed_icon_generation: int = 0
        self._updating_history: bool = False
        self.current_font: tk.font.Font | None = None
        self._current_pin_image: Any = None
        self._drag_anchor_iid: str | None = None
        self._drag_additive: bool = False
        self._drag_base_selection: tuple[str, ...] = ()
        self._drag_last_x: int = 0
        self._drag_last_y: int = 0
        self._drag_scroll_after_id: str | None = None

        self._create_widgets()
        self._bind_events()

    def _create_widgets(self) -> None:
        # Requirements 5.2: self.tree は History_Caller に対して公開しない内部実装詳細である。
        # 唯一の許容された外部参照元は HistoryContextMenu._get_tree()（context_menu.py）のみ。
        self.tree = ttk.Treeview(
            self,
            columns=("hotkey",),
            show="tree headings",
            selectmode="extended",
            style="History.Treeview",
        )
        self._apply_translations()
        self.tree.column("hotkey", width=140, minwidth=100, stretch=False)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.config(yscrollcommand=self.scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _apply_translations(self) -> None:
        """現在の言語に対応するTreeview列見出しを設定する。"""
        self.tree.heading("#0", text=self.app.translator("history_column_label"))
        self.tree.heading("hotkey", text=self.app.translator("hotkey_column_label"))

    def _bind_events(self) -> None:
        self.app.event_dispatcher.subscribe(
            "LANGUAGE_CHANGED", self._apply_translations
        )  # type: ignore
        self.tree.bind("<<TreeviewSelect>>", self._on_history_select)
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<Button-1>", self._on_mouse_press)
        self.tree.bind("<B1-Motion>", self._on_mouse_drag)
        self.tree.bind("<ButtonRelease-1>", self._on_mouse_release)
        from src.gui.base import context_menu
        from src.gui.custom_widgets import bind_context_menu

        history_context_menu: HistoryContextMenu = context_menu.HistoryContextMenu(
            self.master, self.app
        )  # type: ignore
        bind_context_menu(self.tree, history_context_menu.show)

    def _is_additive_modifier(self, state: int) -> bool:
        """OS標準の追加選択修飾キー（macOSはCommand、Windows/LinuxはCtrl）を判定する。"""
        mask = _DARWIN_CMD_MASK if sys.platform == "darwin" else _CTRL_MASK
        return bool(state & mask)

    def _cancel_drag_scroll(self) -> None:
        """予約されているドラッグ自動スクロールのタイマーを解除する。"""
        after_id = getattr(self, "_drag_scroll_after_id", None)
        if after_id is not None:
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
            self._drag_scroll_after_id = None

    def _reset_drag_state(self) -> None:
        """ドラッグ範囲選択に関する一時状態を初期化する。"""
        self._cancel_drag_scroll()
        self._drag_anchor_iid = None
        self._drag_additive = False
        self._drag_base_selection = ()

    def _on_mouse_press(self, event: tk.Event) -> None:
        """左ボタン押下時にデータ行のドラッグ範囲選択を開始する。

        見出しや列区切り線上のクリックは Treeview 標準の列幅変更処理に委ねるため、
        ドラッグアンカーを記録しない。
        """
        self._reset_drag_state()
        if self._updating_history:
            return

        state = int(getattr(event, "state", 0))
        if sys.platform == "darwin" and (state & _CTRL_MASK):
            # macOS では Control+クリックが右クリック（コンテキストメニュー）に割り当てられているため
            # 左ボタンドラッグ選択は開始しない。
            return

        region = self.tree.identify_region(event.x, event.y)
        if region in ("heading", "separator"):
            return

        row_iid = self.tree.identify_row(event.y)
        if not row_iid:
            return

        anchor_iid = row_iid
        if state & _SHIFT_MASK:
            focus_iid = self.tree.focus()
            if focus_iid and self.tree.exists(focus_iid):
                anchor_iid = focus_iid

        self._drag_anchor_iid = anchor_iid
        self._drag_additive = self._is_additive_modifier(state)
        self._drag_base_selection = (
            tuple(self.tree.selection()) if self._drag_additive else ()
        )

    def _on_mouse_drag(self, event: tk.Event) -> None:
        """ドラッグ中のポインタ位置に応じて開始行〜現在行を範囲選択する。"""
        if self._updating_history or not self._drag_anchor_iid:
            return
        if not self.tree.exists(self._drag_anchor_iid):
            self._reset_drag_state()
            return

        self._drag_last_x = event.x
        self._drag_last_y = event.y
        target_iid, scroll_dir = self._resolve_drag_target_and_scroll(event.x, event.y)

        if scroll_dir != 0:
            if self._scroll_and_select(scroll_dir):
                self._schedule_drag_scroll()
            else:
                self._cancel_drag_scroll()
            return

        self._cancel_drag_scroll()
        if target_iid is not None:
            self._apply_drag_range_selection(target_iid)

    def _on_mouse_release(self, event: tk.Event) -> None:
        """左ボタン解放時にドラッグ選択状態を終了する。"""
        self._reset_drag_state()

    def _visible_edge_iid(self, children: tuple[str, ...], *, last: bool) -> str:
        """現在ビューポート内に表示されている先頭または末尾の行 iid を返す。"""
        ordered = reversed(children) if last else children
        for iid in ordered:
            if self.tree.bbox(iid):
                return iid
        return children[-1] if last else children[0]

    def _resolve_drag_target_and_scroll(self, x: int, y: int) -> tuple[str | None, int]:
        """ポインタ座標から選択対象行と自動スクロール方向 (-1/0/1) を決定する。"""
        children = self.tree.get_children("")
        if not children:
            return None, 0

        height = self.tree.winfo_height()
        region = self.tree.identify_region(x, y)

        # データ領域から見出し・区切り線・上端外へドラッグした場合は上方向へ拡張する
        if y < 0 or region in ("heading", "separator"):
            return self._visible_edge_iid(children, last=False), -1

        if height > 1 and y >= height:
            return self._visible_edge_iid(children, last=True), 1

        row_iid = self.tree.identify_row(y)
        if row_iid:
            return row_iid, 0

        # データ領域内の最下部余白へドラッグした場合は末尾行を選択対象とする
        return children[-1], 0

    def _scroll_and_select(self, scroll_dir: int) -> bool:
        """境界外ドラッグ時に1行スクロールし、可視端の行まで選択を拡張する。"""
        yview_top, yview_bottom = self.tree.yview()
        can_scroll = (scroll_dir < 0 and yview_top > 0.0) or (
            scroll_dir > 0 and yview_bottom < 1.0
        )
        if can_scroll:
            self.tree.yview_scroll(scroll_dir, "units")

        children = self.tree.get_children("")
        if children:
            target_iid = self._visible_edge_iid(children, last=(scroll_dir > 0))
            self._apply_drag_range_selection(target_iid)
        return can_scroll

    def _schedule_drag_scroll(self) -> None:
        """ポインタが上下端外にある間、継続的な自動スクロールを予約する。"""
        if self._drag_scroll_after_id is None:
            self._drag_scroll_after_id = self.after(
                _DRAG_SCROLL_INTERVAL_MS, self._perform_drag_scroll_step
            )

    def _perform_drag_scroll_step(self) -> None:
        """予約された自動スクロールの1ステップを実行する。"""
        self._drag_scroll_after_id = None
        if self._updating_history or not self._drag_anchor_iid:
            return
        if not self.tree.exists(self._drag_anchor_iid):
            self._reset_drag_state()
            return

        _, scroll_dir = self._resolve_drag_target_and_scroll(
            self._drag_last_x, self._drag_last_y
        )
        if scroll_dir == 0:
            return
        if self._scroll_and_select(scroll_dir):
            self._schedule_drag_scroll()

    def _apply_drag_range_selection(self, target_iid: str) -> None:
        """ドラッグアンカー行から対象行までの連続範囲を選択状態に反映する。"""
        if not self._drag_anchor_iid:
            return
        children = self.tree.get_children("")
        try:
            anchor_idx = children.index(self._drag_anchor_iid)
            target_idx = children.index(target_iid)
        except ValueError:
            return

        lo, hi = min(anchor_idx, target_idx), max(anchor_idx, target_idx)
        range_iids = children[lo : hi + 1]

        if self._drag_additive:
            selected_set = set(self._drag_base_selection) | set(range_iids)
            new_selection = tuple(iid for iid in children if iid in selected_set)
        else:
            new_selection = range_iids

        if tuple(self.tree.selection()) != new_selection:
            self.tree.selection_set(new_selection)
        if self.tree.focus() != target_iid:
            self.tree.focus(target_iid)

    def _on_double_click(self, event: tk.Event) -> None:
        """Handler for double-click events to copy an item."""
        selected_indices: tuple[int, ...] = self.get_selected_indices()
        if not selected_indices:
            return

        # On double-click, we typically act on the first selected item.
        item_ids: list[float] = self.get_ids_for_indices(selected_indices[:1])
        if item_ids:
            # The event now passes a list of IDs, even if it's just one.
            self.app.event_dispatcher.dispatch("HISTORY_COPY_SELECTED", item_ids)  # type: ignore

    def _on_history_select(self, event: tk.Event) -> None:
        # Requirements 10.1: update_history() の実行中（self._updating_history が True の間）は
        # 選択変更イベントの通知処理を抑制し、ここで早期returnする。
        if self._updating_history:
            return
        # This event is now handled by the parent (main_gui) to update the text widget
        self.app.event_dispatcher.dispatch(
            "HISTORY_SELECTION_CHANGED",
            {  # type: ignore
                "selected_indices": self.get_selected_indices()
            },
        )

    def get_selected_indices(self) -> tuple[int, ...]:
        """現在選択中の表示行を表示順インデックス（0始まり）の昇順タプルで返す。選択が0件の場合は空タプルを返す。"""
        return tuple(sorted(self.tree.index(iid) for iid in self.tree.selection()))

    def get_ids_for_indices(self, indices: Sequence[int]) -> list[float]:
        """表示順インデックスのシーケンスを対応する履歴item IDのリストに変換する。

        `displayed_history` の範囲外のインデックス（負値・上限超過）は結果から除外される。
        `displayed_history` が空の場合は、渡された `indices` の値に関わらず常に空リストを返す。
        """
        return [
            self.displayed_history[i][2]
            for i in indices
            if 0 <= i < len(self.displayed_history)
        ]

    def _iid_for_item_id(self, item_id: float) -> str:
        """履歴item ID（float、一意なタイムスタンプ）からTreeview iid文字列を生成する。"""
        return f"item-{item_id!r}"

    def _format_display_text(self, content: str, index: int) -> str:
        """表示行のテキストを生成する。

        改行・キャリッジリターンを除去した内容の先頭100文字に "..." を付与し、
        表示順インデックス（1始まりの番号）を先頭に付与する。
        ピン留めの装飾は背景色タグ（"pinned"）で行うため、ここでは付与しない。
        """
        display_text = content.replace("\n", " ").replace("\r", "")
        return f"{index + 1}. {display_text[:100]}..."

    def _theme_name(self, theme: dict[str, str]) -> str:
        """テーマ辞書に対応するTHEMES上のテーマ名を返す。

        update_history() は呼出元からテーマ辞書を受け取るため、ThemeManagerの
        現在値ではなく、その辞書自身をTHEMESから逆引きしてアイコンのテーマ名を
        決定する。該当しない辞書はテーマ名を一意に導出できないため拒否する。
        """
        from src.core.config.defaults import THEMES

        for theme_name, theme_values in THEMES.items():
            if theme == theme_values:
                return theme_name
        raise ValueError("theme must match a configured THEMES entry")

    def update_history(
        self,
        history: list[tuple[str, bool, float]],
        theme: dict[str, str],
        hotkey_bindings: Mapping[int, str],
    ) -> None:
        """履歴データ・テーマ・ホットキー割当に基づき、表示を差分更新する。

        `hotkey_bindings` はピン留め履歴IDからキー組み合わせへの対応であり、
        ピン留め済みかつ割当済みの行だけを「ホットキー」列に表示する。
        """
        displayed_hotkey_bindings = dict(hotkey_bindings)
        # アイコンのキャッシュ破棄後は、行が破棄済み画像を指したままになるため再設定が必要（Issue #203）。
        icon_generation: int = getattr(self.app.icon_manager, "cache_generation", 0)
        # 入力が全て同一の場合は何もしない（スクロールと選択状態を100%保護）。
        if (
            self.displayed_history == history
            and self.current_theme == theme
            and self.displayed_hotkey_bindings == displayed_hotkey_bindings
            and self._displayed_icon_generation == icon_generation
        ):
            return

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
            self.displayed_hotkey_bindings = displayed_hotkey_bindings
            self.current_theme = theme
            self._displayed_icon_generation = icon_generation
            pinned_bg_color = theme["pinned_bg"]
            theme_name = self._theme_name(theme)

            new_iids: list[str] = [self._iid_for_item_id(item[2]) for item in history]
            new_iid_set: set[str] = set(new_iids)
            existing_iid_set: set[str] = set(self.tree.get_children(""))

            # 1. 不要になった行を削除（更新後に存在しなくなった表示行のみを削除する: Requirements 2.2）
            stale_iids = existing_iid_set - new_iid_set
            if stale_iids:
                self.tree.delete(*stale_iids)

            # 2. 表示順に挿入・更新・移動
            #    既存行は delete/insert せず item()+move() で内容更新する（Requirements 2.3）
            for index, (content, is_pinned, item_id) in enumerate(history):
                iid = new_iids[index]
                display_text = self._format_display_text(content, index)
                # Requirements 7.1: is_pinned が True の行には "pinned" タグを付与する。
                # Requirements 7.2: is_pinned が False の行には "pinned" タグを付与しない。
                # Issue #195: macOS Aqua テーマでもフォントが反映されるよう全行に "history_item" タグを付与する。
                tags: tuple[str, ...] = (
                    ("history_item", "pinned") if is_pinned else ("history_item",)
                )
                icon_image = (
                    self.app.icon_manager.get_icon("pin", theme_name)
                    if is_pinned and self.app.icon_manager is not None
                    else ""
                )
                if icon_image:
                    self._current_pin_image = icon_image
                elif is_pinned:
                    # アイコン画像が取得できない環境（アセット未配置やヘッドレス等）での安全なテキストフォールバック
                    display_text = f"📌 {display_text}"
                hotkey_combo = (
                    displayed_hotkey_bindings.get(int(item_id), "") if is_pinned else ""
                )

                if iid in existing_iid_set:
                    self.tree.item(
                        iid,
                        text=display_text,
                        tags=tags,
                        image=icon_image,
                        values=(hotkey_combo,),
                    )
                    self.tree.move(iid, "", index)
                else:
                    self.tree.insert(
                        "",
                        index,
                        iid=iid,
                        text=display_text,
                        tags=tags,
                        image=icon_image,
                        values=(hotkey_combo,),
                    )

            # Requirements 7.3: "pinned" タグの背景色は theme["pinned_bg"]（pinned_bg_color）から
            # 取得する。tag_configure は既存・新規行を問わず全ての "pinned" タグ付き行に一括適用される。
            self.tree.tag_configure("pinned", background=pinned_bg_color)
            if self.current_font is not None:
                self.tree.tag_configure("history_item", font=self.current_font)

            # 3. 選択・スクロール状態の復元
            # Requirements 3.1, 3.2: 更新前に選択されていた行のうち、更新後も存在する（tree.exists）行のみを
            # 選択状態に復元する。存在しない行は restored_selection から自動的に除外される。
            restored_selection = tuple(
                iid for iid in prev_selection if self.tree.exists(iid)
            )
            # Requirements 3.3: 更新前が空選択（prev_selection == ()）の場合、restored_selection も
            # 空タプルになり、この if は False となるため selection_set() は呼ばれず、更新後も選択0件のままになる。
            # （selection_set() を空タプルで呼び出すと環境によって tk.TclError になる可能性があるため、
            #   このガードは要件3.3の実現だけでなく安全性の観点でも必須）
            if restored_selection:
                self.tree.selection_set(restored_selection)
            # Requirements 3.4: 更新前のスクロール位置に復元する
            self.tree.yview_moveto(scroll_pos[0])
            drag_anchor = getattr(self, "_drag_anchor_iid", None)
            if drag_anchor is not None and not self.tree.exists(drag_anchor):
                self._reset_drag_state()
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
        self.update_history(
            self.displayed_history,
            theme,
            self.displayed_hotkey_bindings,
        )  # Re-apply pinned colors

    def apply_font(self, font: tk.font.Font) -> None:
        """フォント変更をTreeviewへ適用する。

        Requirements 1.1: History_List_Component は内部の表示ウィジェットとして
        `ttk.Treeview` のインスタンスを常にちょうど1つ保持する。`ttk.Treeview` は
        `tk.Listbox` と異なり `font` 等のウィジェット単位設定を持たず、ttkスタイル
        （`ttk.Style`）経由でのみ見た目を制御できるため、`self.tree.config(font=...)`
        ではなく `ttk.Style` の "Treeview" スタイルにフォントを設定する。

        macOS (Aqua) および行高追従対応 (Issue #195 / CW-0074):
        1. macOS の Aqua テーマでは `style.configure("Treeview", font=...)` が
           ネイティブ描画パイプラインによって無視されるため、全履歴行に付与された
           `"history_item"` タグに対して `self.tree.tag_configure("history_item", font=font)`
           を直接適用する。
        2. `ttk.Treeview` はフォントサイズ変更時に行の高さ（rowheight）を自動調整
           しないため、`font.metrics("linespace")` に基づいて適切な rowheight を動的
           計算し、スタイルに設定する（ピン留めアイコン等が見切れないよう最低22pxを保証）。
        3. 他画面の Treeview へ影響を与えないよう、専用スタイル "History.Treeview" と
           グローバル "Treeview" の双方へ安全に適用する。
        """
        self.current_font = font

        # 1. 行の高さ（rowheight）の動的計算
        try:
            linespace = font.metrics("linespace")
        except Exception:
            try:
                size = font.cget("size")
                linespace = abs(int(size)) + 4
            except Exception:
                linespace = 14
        rowheight = max(linespace + 8, 22)

        # 2. スタイルへの設定（専用スタイル & グローバルスタイル）
        try:
            style = ttk.Style(self)
            style.configure("History.Treeview", font=font, rowheight=rowheight)
            style.configure("Treeview", font=font, rowheight=rowheight)
        except Exception:
            pass

        # 3. macOS (Aqua) 向けのタグフォント強制適用
        try:
            self.tree.tag_configure("history_item", font=font)
        except Exception:
            pass
