from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from src.core.config.defaults import THEMES
from src.gui.components.history_list_component import HistoryListComponent


class RecordingTree:
    """Treeview の更新結果を保持する、画面不要の最小テスト実装。"""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.item_calls: list[tuple[str, dict[str, Any]]] = []
        self.insert_calls: list[tuple[str, int, str, dict[str, Any]]] = []

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
        assert tag == "pinned"
        assert "background" in options

    def exists(self, iid: str) -> bool:
        return iid in self.rows

    def selection_set(self, iids: tuple[str, ...]) -> None:
        assert iids

    def yview_moveto(self, fraction: float) -> None:
        assert fraction == 0.0


class RecordingIconManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

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
    component.current_theme = {}
    component._updating_history = False
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

    component.update_history([("first", True, 1.0), ("second", False, 2.0)], theme)
    component.update_history([("first", False, 1.0), ("second", True, 2.0)], theme)

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

    component.update_history(history, THEMES["light"])
    component.apply_theme(THEMES["dark"])

    assert component.displayed_history == history
    assert icon_manager.calls == [("pin", "light"), ("pin", "dark")]
    assert tree.rows["item-1.0"]["image"] == "pin-dark-icon"
    assert tree.rows["item-2.0"]["image"] == ""
    assert [(iid, options["image"]) for iid, options in tree.item_calls] == [
        ("item-1.0", "pin-dark-icon"),
        ("item-2.0", ""),
    ]

