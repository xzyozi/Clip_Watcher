from __future__ import annotations

import sys
import tkinter as tk
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.config.defaults import THEMES
from src.gui.components.history_list_component import HistoryListComponent


class RecordingTree:
    """Treeview の更新結果を保持する、画面不要の最小テスト実装。"""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.item_calls: list[tuple[str, dict[str, Any]]] = []
        self.insert_calls: list[tuple[str, int, str, dict[str, Any]]] = []
        self.tag_configure_calls: list[tuple[str, dict[str, Any]]] = []

    def selection(self) -> tuple[str, ...]:
        return ()

    def yview(self) -> tuple[float, float]:
        return (0.0, 1.0)

    def get_children(self, parent: str) -> tuple[str, ...]:
        assert parent == ""
        return tuple(self.rows)

    def delete(self, *iids: str) -> None:
        for iid in iids:
            del self.rows[iid]

    def item(self, iid: str, **options: Any) -> None:
        self.item_calls.append((iid, options))
        self.rows[iid].update(options)

    def move(self, iid: str, parent: str, index: int) -> None:
        assert parent == ""
        assert iid in self.rows
        assert index >= 0

    def insert(self, parent: str, index: int, iid: str, **options: Any) -> str:
        assert parent == ""
        self.insert_calls.append((parent, index, iid, options))
        self.rows[iid] = options
        return iid

    def tag_configure(self, tag: str, **options: Any) -> None:
        self.tag_configure_calls.append((tag, options))

    def exists(self, iid: str) -> bool:
        return iid in self.rows

    def selection_set(self, iids: tuple[str, ...]) -> None:
        assert iids

    def yview_moveto(self, fraction: float) -> None:
        assert fraction == 0.0


class RecordingIconManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.cache_generation: int = 0

    def get_icon(self, icon_name: str, theme_name: str) -> str:
        self.calls.append((icon_name, theme_name))
        return f"{icon_name}-{theme_name}-icon"


def make_component(
    tree: RecordingTree, icon_manager: RecordingIconManager
) -> HistoryListComponent:
    """update_history の公開境界を画面初期化なしでテスト可能にする。"""
    component = HistoryListComponent.__new__(HistoryListComponent)
    component.app = SimpleNamespace(
        icon_manager=icon_manager,
        theme_manager=SimpleNamespace(get_current_theme=lambda: "dark"),
    )
    component.tree = tree
    component.displayed_history = []
    component.displayed_hotkey_bindings = {}
    component.current_theme = {}
    component._displayed_icon_generation = 0
    component._updating_history = False
    component.current_font = None
    component._current_pin_image = None
    return component


def test_theme_name_derives_configured_identifier_from_theme_dictionary() -> None:
    """要件4.1: 渡されたテーマ辞書からIconManager用のテーマ名を導出する。"""
    component = HistoryListComponent.__new__(HistoryListComponent)

    assert component._theme_name(THEMES["light"]) == "light"
    assert component._theme_name(THEMES["dark"]) == "dark"


def test_update_history_sets_images_for_new_pinned_and_unpinned_rows() -> None:
    """要件4.1・4.2: 新規行にはピン状態に対応する image を必ず設定する。"""
    tree = RecordingTree()
    icon_manager = RecordingIconManager()
    component = make_component(tree, icon_manager)

    component.update_history(
        [("pinned", True, 1.0), ("not pinned", False, 2.0)],
        THEMES["light"],
        {},
    )

    assert icon_manager.calls == [("pin", "light")]
    assert tree.rows["item-1.0"]["image"] == "pin-light-icon"
    assert tree.rows["item-2.0"]["image"] == ""
    assert all("image" in options for _, _, _, options in tree.insert_calls)


def test_update_history_replaces_images_when_existing_row_pin_state_changes() -> None:
    """要件4.3: iidを再利用する行でもピン状態の変更を image に反映する。"""
    tree = RecordingTree()
    icon_manager = RecordingIconManager()
    component = make_component(tree, icon_manager)
    theme = THEMES["dark"]

    component.update_history([("first", True, 1.0), ("second", False, 2.0)], theme, {})
    component.update_history([("first", False, 1.0), ("second", True, 2.0)], theme, {})

    assert tree.rows["item-1.0"]["image"] == ""
    assert tree.rows["item-2.0"]["image"] == "pin-dark-icon"
    assert [(iid, options["image"]) for iid, options in tree.item_calls] == [
        ("item-1.0", ""),
        ("item-2.0", "pin-dark-icon"),
    ]


def test_apply_theme_reapplies_pinned_icon_using_new_theme_name() -> None:
    """要件5.1・5.2: テーマ変更時は表示済みのピン行へ新テーマの画像を再設定する。"""
    tree = RecordingTree()
    icon_manager = RecordingIconManager()
    component = make_component(tree, icon_manager)
    history = [("pinned", True, 1.0), ("not pinned", False, 2.0)]

    component.update_history(history, THEMES["light"], {})
    component.apply_theme(THEMES["dark"])

    assert component.displayed_history == history
    assert icon_manager.calls == [("pin", "light"), ("pin", "dark")]
    assert tree.rows["item-1.0"]["image"] == "pin-dark-icon"
    assert tree.rows["item-2.0"]["image"] == ""
    assert [(iid, options["image"]) for iid, options in tree.item_calls] == [
        ("item-1.0", "pin-dark-icon"),
        ("item-2.0", ""),
    ]


def test_update_history_reassigns_images_after_icon_cache_invalidation() -> None:
    """Issue #203: 同一入力でもアイコンキャッシュ破棄後は行の image を再設定する。"""
    tree = RecordingTree()
    icon_manager = RecordingIconManager()
    component = make_component(tree, icon_manager)
    history = [("pinned", True, 1.0)]
    theme = THEMES["dark"]

    component.update_history(history, theme, {})
    component.update_history(history, theme, {})  # 世代不変なら早期return
    assert len(tree.item_calls) == 0
    assert icon_manager.calls == [("pin", "dark")]

    icon_manager.cache_generation += 1
    component.update_history(history, theme, {})

    assert icon_manager.calls == [("pin", "dark"), ("pin", "dark")]
    assert [(iid, options["image"]) for iid, options in tree.item_calls] == [
        ("item-1.0", "pin-dark-icon")
    ]


def test_update_history_displays_hotkeys_only_for_pinned_bound_items() -> None:
    """設定済みのピン留め履歴だけにホットキー列の値を表示する。"""
    tree = RecordingTree()
    component = make_component(tree, RecordingIconManager())

    component.update_history(
        [
            ("assigned", True, 1.0),
            ("unassigned", True, 2.0),
            ("unpinned", False, 3.0),
        ],
        THEMES["light"],
        {1: "Ctrl+Alt+1", 3: "Ctrl+Alt+3"},
    )

    assert tree.rows["item-1.0"]["values"] == ("Ctrl+Alt+1",)
    assert tree.rows["item-2.0"]["values"] == ("",)
    assert tree.rows["item-3.0"]["values"] == ("",)


def test_update_history_refreshes_existing_row_when_only_hotkey_changes() -> None:
    """履歴・テーマが不変でも、割当変更を既存行のホットキー列へ反映する。"""
    tree = RecordingTree()
    component = make_component(tree, RecordingIconManager())
    history = [("pinned", True, 1.0)]

    component.update_history(history, THEMES["light"], {})
    component.update_history(history, THEMES["light"], {1: "Ctrl+Alt+1"})

    assert tree.rows["item-1.0"]["values"] == ("Ctrl+Alt+1",)
    assert tree.item_calls[-1][0] == "item-1.0"
    assert tree.item_calls[-1][1]["values"] == ("Ctrl+Alt+1",)


def test_update_history_applies_history_item_tag_to_all_rows() -> None:
    """Issue #195: 全行に "history_item" タグを付与し、ピン留め行には "pinned" も付与する。"""
    tree = RecordingTree()
    component = make_component(tree, RecordingIconManager())
    history = [("pinned item", True, 1.0), ("normal item", False, 2.0)]

    component.update_history(history, THEMES["light"], {})

    assert tree.rows["item-1.0"]["tags"] == ("history_item", "pinned")
    assert tree.rows["item-2.0"]["tags"] == ("history_item",)


def test_update_history_reconfigures_history_item_font_when_current_font_is_set() -> (
    None
):
    """Issue #195: current_font が設定されている場合、update_history で history_item タグにフォントを再設定する。"""
    tree = RecordingTree()
    component = make_component(tree, RecordingIconManager())
    dummy_font = SimpleNamespace(metrics=lambda k: 20, cget=lambda k: 14)
    component.current_font = dummy_font  # type: ignore[assignment]

    component.update_history([("item", False, 1.0)], THEMES["light"], {})

    assert ("history_item", {"font": dummy_font}) in tree.tag_configure_calls
    assert (
        "pinned",
        {"background": THEMES["light"]["pinned_bg"]},
    ) in tree.tag_configure_calls


def test_apply_font_calculates_rowheight_and_configures_tag(monkeypatch: Any) -> None:
    """Issue #195: apply_font が rowheight を動的計算し、スタイルとタグへ設定する。"""
    tree = RecordingTree()
    component = make_component(tree, RecordingIconManager())
    style_calls: list[tuple[str, dict[str, Any]]] = []

    class MockStyle:
        def __init__(self, master: Any = None) -> None:
            pass

        def configure(self, style_name: str, **kwargs: Any) -> None:
            style_calls.append((style_name, kwargs))

    monkeypatch.setattr(
        "src.gui.components.history_list_component.ttk.Style", MockStyle
    )

    dummy_font = SimpleNamespace(metrics=lambda k: 18, cget=lambda k: 12)
    component.apply_font(dummy_font)  # type: ignore[arg-type]

    assert component.current_font is dummy_font
    # rowheight = max(18 + 8, 22) = 26
    assert ("History.Treeview", {"font": dummy_font, "rowheight": 26}) in style_calls
    assert ("history_item", {"font": dummy_font}) in tree.tag_configure_calls


def test_apply_font_enforces_minimum_rowheight(monkeypatch: Any) -> None:
    """Issue #195: 極小フォントでもピン留めアイコンが見切れないよう最低22pxの rowheight を保証する。"""
    tree = RecordingTree()
    component = make_component(tree, RecordingIconManager())
    style_calls: list[tuple[str, dict[str, Any]]] = []

    class MockStyle:
        def __init__(self, master: Any = None) -> None:
            pass

        def configure(self, style_name: str, **kwargs: Any) -> None:
            style_calls.append((style_name, kwargs))

    monkeypatch.setattr(
        "src.gui.components.history_list_component.ttk.Style", MockStyle
    )

    dummy_font = SimpleNamespace(metrics=lambda k: 10, cget=lambda k: 8)
    component.apply_font(dummy_font)  # type: ignore[arg-type]

    # rowheight = max(10 + 8, 22) = 22
    assert ("History.Treeview", {"font": dummy_font, "rowheight": 22}) in style_calls


def test_update_history_retains_image_reference_and_no_text_prefix_when_icon_present() -> (
    None
):
    """Issue CW-0078: 画像取得時はテキストを二重装飾せず画像のみを設定し、参照を保持する（Windows互換）。"""
    tree = RecordingTree()
    icon_manager = RecordingIconManager()
    component = make_component(tree, icon_manager)
    history = [("pinned item", True, 1.0)]

    component.update_history(history, THEMES["light"], {})

    assert component._current_pin_image == "pin-light-icon"
    # テキスト先頭に絵文字が混入せず、元のインデックス表示のままであること
    assert tree.rows["item-1.0"]["text"] == "1. pinned item..."
    assert tree.rows["item-1.0"]["image"] == "pin-light-icon"


def test_update_history_falls_back_to_pin_symbol_when_icon_missing() -> None:
    """Issue CW-0078: アイコン画像が取得できない環境ではテキスト先頭にピン記号をフォールバック付与する。"""
    tree = RecordingTree()
    component = make_component(tree, None)  # type: ignore[arg-type]
    history = [("pinned item", True, 1.0), ("normal item", False, 2.0)]

    component.update_history(history, THEMES["light"], {})

    assert tree.rows["item-1.0"]["text"] == "📌 1. pinned item..."
    assert tree.rows["item-1.0"]["image"] == ""
    assert tree.rows["item-2.0"]["text"] == "2. normal item..."
    assert tree.rows["item-2.0"]["image"] == ""


@pytest.fixture
def real_history_component(
    tk_root: tk.Tk,
) -> Generator[
    tuple[HistoryListComponent, tk.Toplevel, list[tuple[str, Any]]], None, None
]:
    """実 Tk 上に配置した HistoryListComponent とディスパッチ記録を返す。"""
    top = tk.Toplevel(tk_root)
    top.geometry("420x160+0+0")
    dispatched: list[tuple[str, Any]] = []

    dispatcher = MagicMock()
    dispatcher.dispatch.side_effect = lambda name, payload=None: dispatched.append(
        (name, payload)
    )
    app = MagicMock()
    app.translator = lambda key: key
    app.icon_manager = None
    app.event_dispatcher = dispatcher
    app.undo_manager.can_undo.return_value = False

    component = HistoryListComponent(top, app)
    component.pack(fill=tk.BOTH, expand=True)
    app.gui = SimpleNamespace(history_component=component)

    yield component, top, dispatched

    component._cancel_drag_scroll()
    top.destroy()


def _row_center(component: HistoryListComponent, iid: str) -> tuple[int, int]:
    bbox = component.tree.bbox(iid)
    assert bbox, f"{iid} is not visible"
    x, y, _, height = bbox
    return int(x) + 10, int(y) + max(1, int(height) // 2)


def test_drag_selection_selects_contiguous_range_down_up_and_shrink(
    real_history_component: tuple[
        HistoryListComponent, tk.Toplevel, list[tuple[str, Any]]
    ],
) -> None:
    """Issue #219: 実 Tk 上で下方向・上方向・縮小ドラッグにより連続範囲が選択される。"""
    component, top, dispatched = real_history_component
    history = [(f"item {i}", False, float(i)) for i in range(6)]
    component.update_history(history, THEMES["light"], {})
    top.update()

    # 下方向ドラッグ: 0 -> 3
    x0, y0 = _row_center(component, "item-0.0")
    x3, y3 = _row_center(component, "item-3.0")
    component.tree.event_generate("<Button-1>", x=x0, y=y0, state=0)
    component.tree.event_generate("<B1-Motion>", x=x3, y=y3, state=0x0100)
    component.tree.event_generate("<ButtonRelease-1>", x=x3, y=y3, state=0x0100)
    top.update()

    assert component.tree.selection() == (
        "item-0.0",
        "item-1.0",
        "item-2.0",
        "item-3.0",
    )
    assert component.get_selected_indices() == (0, 1, 2, 3)
    assert any(
        name == "HISTORY_SELECTION_CHANGED"
        and payload == {"selected_indices": (0, 1, 2, 3)}
        for name, payload in dispatched
    )

    # 上方向ドラッグ: 4 -> 2
    x4, y4 = _row_center(component, "item-4.0")
    x2, y2 = _row_center(component, "item-2.0")
    component.tree.event_generate("<Button-1>", x=x4, y=y4, state=0)
    component.tree.event_generate("<B1-Motion>", x=x2, y=y2, state=0x0100)
    component.tree.event_generate("<ButtonRelease-1>", x=x2, y=y2, state=0x0100)
    top.update()

    assert component.tree.selection() == ("item-2.0", "item-3.0", "item-4.0")

    # 縮小方向ドラッグ: 0 -> 4 -> 1
    x1, y1 = _row_center(component, "item-1.0")
    component.tree.event_generate("<Button-1>", x=x0, y=y0, state=0)
    component.tree.event_generate("<B1-Motion>", x=x4, y=y4, state=0x0100)
    component.tree.event_generate("<B1-Motion>", x=x1, y=y1, state=0x0100)
    component.tree.event_generate("<ButtonRelease-1>", x=x1, y=y1, state=0x0100)
    top.update()

    assert component.tree.selection() == ("item-0.0", "item-1.0")


def test_drag_on_separator_resizes_column_without_row_selection(
    real_history_component: tuple[
        HistoryListComponent, tk.Toplevel, list[tuple[str, Any]]
    ],
) -> None:
    """Issue #219: 列区切り線上のドラッグでは列幅変更が動作し、行選択が発動しない。"""
    component, top, _ = real_history_component
    history = [(f"item {i}", False, float(i)) for i in range(5)]
    component.update_history(history, THEMES["light"], {})
    top.update()

    orig_w = int(component.tree.column("#0", "width"))
    sep_x = next(
        (
            x
            for x in range(max(0, orig_w - 10), orig_w + 10)
            if component.tree.identify_region(x, 10) == "separator"
        ),
        None,
    )
    assert sep_x is not None

    component.tree.event_generate("<Button-1>", x=sep_x, y=10, state=0)
    assert component._drag_anchor_iid is None

    component.tree.event_generate("<B1-Motion>", x=sep_x - 40, y=10, state=0x0100)
    during_w = int(component.tree.column("#0", "width"))
    component.tree.event_generate("<ButtonRelease-1>", x=sep_x - 40, y=10, state=0x0100)
    top.update()

    assert during_w < orig_w
    assert component.tree.selection() == ()


def test_additive_drag_preserves_existing_selection(
    real_history_component: tuple[
        HistoryListComponent, tk.Toplevel, list[tuple[str, Any]]
    ],
) -> None:
    """Issue #219: Ctrl(macOSはCmd)押下中のドラッグは既存選択を維持して範囲を追加する。"""
    component, top, _ = real_history_component
    history = [(f"item {i}", False, float(i)) for i in range(6)]
    component.update_history(history, THEMES["light"], {})
    top.update()

    # まず行0を選択
    x0, y0 = _row_center(component, "item-0.0")
    component.tree.event_generate("<Button-1>", x=x0, y=y0, state=0)
    component.tree.event_generate("<ButtonRelease-1>", x=x0, y=y0, state=0x0100)
    top.update()
    assert component.tree.selection() == ("item-0.0",)

    # OS標準の追加修飾キー付きで行2 -> 行4をドラッグ
    mod_mask = 0x0008 if sys.platform == "darwin" else 0x0004
    x2, y2 = _row_center(component, "item-2.0")
    x4, y4 = _row_center(component, "item-4.0")
    component.tree.event_generate("<Button-1>", x=x2, y=y2, state=mod_mask)
    component.tree.event_generate("<B1-Motion>", x=x4, y=y4, state=0x0100 | mod_mask)
    component.tree.event_generate(
        "<ButtonRelease-1>", x=x4, y=y4, state=0x0100 | mod_mask
    )
    top.update()

    assert component.tree.selection() == (
        "item-0.0",
        "item-2.0",
        "item-3.0",
        "item-4.0",
    )


def test_drag_past_edges_scrolls_and_extends_selection(
    real_history_component: tuple[
        HistoryListComponent, tk.Toplevel, list[tuple[str, Any]]
    ],
) -> None:
    """Issue #219: ツリー上端・下端を越えたドラッグで自動スクロールし選択範囲を拡張する。"""
    component, top, _ = real_history_component
    history = [(f"item {i}", False, float(i)) for i in range(20)]
    component.update_history(history, THEMES["light"], {})
    top.update()

    # 下端外ドラッグで下へスクロール＆選択拡張
    x0, y0 = _row_center(component, "item-0.0")
    yview_before = component.tree.yview()
    assert yview_before[1] < 1.0

    component.tree.event_generate("<Button-1>", x=x0, y=y0, state=0)
    component.tree.event_generate(
        "<B1-Motion>", x=x0, y=component.tree.winfo_height() + 20, state=0x0100
    )
    component.tree.event_generate(
        "<ButtonRelease-1>", x=x0, y=component.tree.winfo_height() + 20, state=0x0100
    )
    top.update()

    yview_after_down = component.tree.yview()
    assert yview_after_down[0] > yview_before[0]
    assert len(component.tree.selection()) > 1

    # スクロール途中位置から上端外ドラッグで上へスクロール＆選択拡張
    component.tree.yview_moveto(0.4)
    top.update()
    # 可視範囲内で見切れていない2番目の行を特定してドラッグ開始
    # （最下行は部分表示だと <Button-1> の BrowseTo -> see で下に自動スクロールするため）
    visible_iids = [
        iid for iid in component.tree.get_children("") if component.tree.bbox(iid)
    ]
    assert len(visible_iids) >= 2
    start_iid = visible_iids[1]
    xs, ys = _row_center(component, start_iid)

    component.tree.event_generate("<Button-1>", x=xs, y=ys, state=0)
    top.update()
    yview_after_press = component.tree.yview()
    assert yview_after_press[0] > 0.0

    component.tree.event_generate("<B1-Motion>", x=xs, y=-10, state=0x0100)
    component.tree.event_generate("<ButtonRelease-1>", x=xs, y=-10, state=0x0100)
    top.update()

    yview_after_up = component.tree.yview()
    assert yview_after_up[0] < yview_after_press[0]
    assert start_iid in component.tree.selection()
    assert len(component.tree.selection()) > 1


def test_drag_selection_suppressed_during_update_history(
    real_history_component: tuple[
        HistoryListComponent, tk.Toplevel, list[tuple[str, Any]]
    ],
) -> None:
    """Issue #219: _updating_history 中はドラッグ選択や通知が抑制される。"""
    component, top, dispatched = real_history_component
    history = [(f"item {i}", False, float(i)) for i in range(4)]
    component.update_history(history, THEMES["light"], {})
    top.update()
    dispatched.clear()

    x0, y0 = _row_center(component, "item-0.0")
    x3, y3 = _row_center(component, "item-3.0")

    component._updating_history = True
    try:
        component.tree.event_generate("<Button-1>", x=x0, y=y0, state=0)
        component.tree.event_generate("<B1-Motion>", x=x3, y=y3, state=0x0100)
        component.tree.event_generate("<ButtonRelease-1>", x=x3, y=y3, state=0x0100)
        top.update()
    finally:
        component._updating_history = False

    assert component._drag_anchor_iid is None
    assert not any(name == "HISTORY_SELECTION_CHANGED" for name, _ in dispatched)


def test_is_additive_modifier_respects_platform(monkeypatch: Any) -> None:
    """プラットフォームに応じた追加選択修飾キー判定を検証する。"""
    component = HistoryListComponent.__new__(HistoryListComponent)

    monkeypatch.setattr(sys, "platform", "darwin")
    assert component._is_additive_modifier(0x0008) is True
    assert component._is_additive_modifier(0x0004) is False

    monkeypatch.setattr(sys, "platform", "win32")
    assert component._is_additive_modifier(0x0004) is True
    assert component._is_additive_modifier(0x0008) is False

    monkeypatch.setattr(sys, "platform", "linux")
    assert component._is_additive_modifier(0x0004) is True
    assert component._is_additive_modifier(0x0010) is False  # NumLock を誤判定しない


def test_right_click_inside_drag_selection_keeps_multiple_selection(
    real_history_component: tuple[
        HistoryListComponent, tk.Toplevel, list[tuple[str, Any]]
    ],
) -> None:
    """ドラッグで複数選択後に選択内行を右クリックしても複数選択が維持される。"""
    from src.gui.base.context_menu import HistoryContextMenu

    component, top, _ = real_history_component
    history = [(f"item {i}", False, float(i)) for i in range(5)]
    component.update_history(history, THEMES["light"], {})
    top.update()

    x1, y1 = _row_center(component, "item-1.0")
    x3, y3 = _row_center(component, "item-3.0")
    component.tree.event_generate("<Button-1>", x=x1, y=y1, state=0)
    component.tree.event_generate("<B1-Motion>", x=x3, y=y3, state=0x0100)
    component.tree.event_generate("<ButtonRelease-1>", x=x3, y=y3, state=0x0100)
    top.update()

    assert component.get_selected_indices() == (1, 2, 3)

    # 選択範囲内の行2上で右クリックメニュー状態を取得
    ctx = HistoryContextMenu(top, component.app)
    x2, y2 = _row_center(component, "item-2.0")
    event = SimpleNamespace(y=y2, x_root=x2, y_root=y2)
    row_iid = component.tree.identify_row(event.y)
    assert row_iid == "item-2.0"
    assert row_iid in component.tree.selection()

    state = ctx.state_provider.get_menu_state(component.tree)
    assert state.selected_indices == (1, 2, 3)
    assert state.selected_ids == [1.0, 2.0, 3.0]
