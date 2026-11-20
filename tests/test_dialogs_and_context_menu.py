"""ダイアログ（フォーマット選択・クイックタスク・ホットキー割当）とコンテキストメニューのテスト。

実 Tk を使い、モーダル待機（wait_window）と grab_set だけを無効化する。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.gui.base.context_menu import (
    BaseContextMenu,
    HistoryContextMenu,
    HistoryMenuStateProvider,
    PhraseListContextMenu,
)
from src.gui.dialogs.format_dialog import FormatDialog
from src.gui.dialogs.pinned_hotkey_dialog import PinnedHotkeyDialog
from src.gui.windows.quick_task_dialog import QuickTaskDialog


@pytest.fixture(autouse=True)
def _no_modal(monkeypatch: pytest.MonkeyPatch) -> None:
    """モーダル系の呼び出しがテストをブロックしないよう無効化する。"""
    monkeypatch.setattr(tk.Toplevel, "grab_set", lambda self: None)
    monkeypatch.setattr(tk.Toplevel, "wait_window", lambda self, window=None: None)


@pytest.fixture
def app() -> MagicMock:
    app = MagicMock()
    app.translator = lambda key: key
    app.theme_manager = MagicMock(
        spec=["get_current_theme", "apply_theme_to_widget_tree"]
    )
    app.theme_manager.get_current_theme.return_value = "light"
    return app


# --- FormatDialog ---


def _plugin(name: str) -> MagicMock:
    plugin = MagicMock()
    plugin.name = name
    return plugin


def _buttons(widget: tk.Misc) -> list[Any]:
    found: list[Any] = []
    for child in widget.winfo_children():
        if child.winfo_class() == "TButton":
            found.append(child)
        found.extend(_buttons(child))
    return found


def test_format_dialog_lists_plugins_and_returns_selected_one(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    plugins = [_plugin("Upper"), _plugin("Lower")]
    app.plugin_manager.get_available_plugins.return_value = plugins
    dialog = FormatDialog(tk_root, app, MagicMock())

    labels = [str(b.cget("text")) for b in _buttons(dialog)]
    assert labels == ["Upper", "Lower", "Cancel"]

    _buttons(dialog)[1].invoke()
    assert dialog.selected_plugin is plugins[1]
    assert not dialog.winfo_exists()


def test_format_dialog_cancel_leaves_no_selection(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    app.plugin_manager.get_available_plugins.return_value = [_plugin("Upper")]
    dialog = FormatDialog(tk_root, app, MagicMock())
    dialog.selected_plugin = app.plugin_manager.get_available_plugins()[0]
    _buttons(dialog)[-1].invoke()
    assert dialog.selected_plugin is None
    assert not dialog.winfo_exists()


# --- QuickTaskDialog ---


@pytest.fixture
def quick_dialog(
    tk_root: tk.Tk, app: MagicMock
) -> Generator[QuickTaskDialog, None, None]:
    settings = MagicMock()
    settings.get_setting.return_value = False
    dialog = QuickTaskDialog(tk_root, app, settings, ["task A\n\n  task B  ", "task C"])
    yield dialog
    if dialog.winfo_exists():
        dialog.destroy()


def test_quick_task_splits_lines_and_skips_blank_rows(
    quick_dialog: QuickTaskDialog,
) -> None:
    assert quick_dialog.get_remaining_tasks() == ["task A", "task B", "task C"]


def test_quick_task_add_tasks_appends_rows(quick_dialog: QuickTaskDialog) -> None:
    quick_dialog.add_tasks(["task D"])
    assert quick_dialog.get_remaining_tasks()[-1] == "task D"


def test_quick_task_without_tasks_starts_empty(tk_root: tk.Tk, app: MagicMock) -> None:
    settings = MagicMock()
    settings.get_setting.return_value = False
    dialog = QuickTaskDialog(tk_root, app, settings)
    try:
        assert dialog.get_remaining_tasks() == []
    finally:
        dialog.destroy()


def test_quick_task_copy_keeps_row_when_delete_disabled(
    app: MagicMock, quick_dialog: QuickTaskDialog
) -> None:
    first = quick_dialog.task_list.get_children()[0]
    quick_dialog.task_list.selection_set(first)
    quick_dialog._copy_selected()
    app.monitor.update_clipboard.assert_called_once_with("task A")
    assert len(quick_dialog.get_remaining_tasks()) == 3


def test_quick_task_copy_removes_rows_and_closes_after_last(
    app: MagicMock, quick_dialog: QuickTaskDialog
) -> None:
    quick_dialog.delete_on_copy.set(True)
    for _ in range(3):
        children = quick_dialog.task_list.get_children()
        if not children:
            break
        quick_dialog.task_list.selection_set(children[0])
        quick_dialog._copy_selected()
    assert app.monitor.update_clipboard.call_count == 3
    assert not quick_dialog.winfo_exists()


def test_quick_task_checkbox_persists_setting(quick_dialog: QuickTaskDialog) -> None:
    quick_dialog.delete_on_copy.set(True)
    quick_dialog._save_delete_on_copy_setting()
    quick_dialog.settings_manager.set_setting.assert_called_once_with(
        "quick_task_delete_on_copy", True
    )
    quick_dialog.settings_manager.save_settings.assert_called_once()


# --- PinnedHotkeyDialog ---


@pytest.fixture
def hotkey_dialog(tk_root: tk.Tk) -> Generator[PinnedHotkeyDialog, None, None]:
    saved: list[str] = []
    dialog = PinnedHotkeyDialog(
        tk_root, "Ctrl+A", lambda combo: not saved.append(combo)
    )
    dialog.saved = saved  # type: ignore[attr-defined]
    yield dialog
    if dialog.winfo_exists():
        dialog.destroy()


def _key(keysym: str, state: int = 0, char: str = "") -> SimpleNamespace:
    return SimpleNamespace(keysym=keysym, state=state, char=char)


def test_hotkey_dialog_starts_with_initial_combo(
    hotkey_dialog: PinnedHotkeyDialog,
) -> None:
    assert hotkey_dialog._combo.get() == "Ctrl+A"


def test_hotkey_dialog_without_initial_combo_is_blank(tk_root: tk.Tk) -> None:
    dialog = PinnedHotkeyDialog(tk_root, None, lambda combo: True)
    try:
        assert dialog._combo.get() == ""
    finally:
        dialog.destroy()


@pytest.mark.parametrize(
    ("keysym", "state", "char", "expected"),
    [
        ("b", 0x0004, "b", "Ctrl+B"),
        ("c", 0x0004 | 0x0001, "c", "Ctrl+Shift+C"),
        ("d", 0x0020, "d", "Alt+D"),
        ("e", 0x0008, "e", "Alt+E"),
        ("5", 0x0004, "5", "Ctrl+5"),
        ("eacute", 0x0004, "é", "Ctrl+É"),
    ],
)
def test_hotkey_dialog_builds_combo_from_modifier_and_key(
    hotkey_dialog: PinnedHotkeyDialog,
    keysym: str,
    state: int,
    char: str,
    expected: str,
) -> None:
    assert hotkey_dialog._on_key_press(_key(keysym, state, char)) == "break"  # type: ignore[arg-type]
    assert hotkey_dialog._combo.get() == expected


def test_hotkey_dialog_ignores_bare_modifier_keys(
    hotkey_dialog: PinnedHotkeyDialog,
) -> None:
    assert hotkey_dialog._on_key_press(_key("Control_L", 0x0004)) is None  # type: ignore[arg-type]
    assert hotkey_dialog._combo.get() == "Ctrl+A"


def test_hotkey_dialog_requires_a_modifier_and_a_supported_key(
    hotkey_dialog: PinnedHotkeyDialog,
) -> None:
    assert hotkey_dialog._on_key_press(_key("a", 0, "a")) == "break"  # type: ignore[arg-type]
    assert hotkey_dialog._combo.get() == "Ctrl+A"  # 修飾キーなしは変更しない
    assert hotkey_dialog._on_key_press(_key("F5", 0x0004, "")) == "break"  # type: ignore[arg-type]
    assert hotkey_dialog._combo.get() == "Ctrl+A"  # 英数字以外は変更しない


def test_hotkey_dialog_backspace_clears_combo(
    hotkey_dialog: PinnedHotkeyDialog,
) -> None:
    assert hotkey_dialog._on_key_press(_key("BackSpace")) == "break"  # type: ignore[arg-type]
    assert hotkey_dialog._combo.get() == ""


def test_hotkey_dialog_save_closes_only_when_accepted(tk_root: tk.Tk) -> None:
    results = iter([False, True])
    seen: list[str] = []

    def on_save(combo: str) -> bool:
        seen.append(combo)
        return next(results)

    dialog = PinnedHotkeyDialog(tk_root, "Ctrl+Z", on_save)
    dialog._save()
    assert dialog.winfo_exists()  # 拒否された場合は開いたまま
    dialog._save()
    assert not dialog.winfo_exists()
    assert seen == ["Ctrl+Z", "Ctrl+Z"]


# --- コンテキストメニュー ---


class _FakeTree:
    """Treeview の選択・行特定だけを備えた最小実装。"""

    def __init__(self, rows: list[str], selected: list[str]) -> None:
        self.rows = rows
        self._selected = selected
        self.focused: str | None = None

    def selection(self) -> tuple[str, ...]:
        return tuple(self._selected)

    def selection_set(self, iid: str) -> None:
        self._selected = [iid]

    def index(self, iid: str) -> int:
        return self.rows.index(iid)

    def identify_row(self, y: int) -> str:
        return self.rows[y] if 0 <= y < len(self.rows) else ""

    def focus(self, iid: str) -> None:
        self.focused = iid


def _history_app(
    app: MagicMock, displayed: list[tuple[str, bool, float]], *, can_undo: bool
) -> MagicMock:
    component = MagicMock()
    component.displayed_history = displayed
    component.get_ids_for_indices.side_effect = lambda idx: [
        displayed[i][2] for i in idx
    ]
    app.gui.history_component = component
    app.undo_manager.can_undo.return_value = can_undo
    app.event_dispatcher = MagicMock()
    app.get_pinned_hotkey_combo.return_value = None
    return app


def _labels(menu: tk.Menu) -> list[str]:
    last = menu.index("end")
    if last is None:
        return []
    labels = []
    for i in range(last + 1):
        labels.append(
            "-" if menu.type(i) == "separator" else str(menu.entrycget(i, "label"))
        )
    return labels


def test_menu_state_reflects_selection_pin_and_undo(app: MagicMock) -> None:
    displayed = [("a", False, 1.0), ("b", True, 2.0)]
    _history_app(app, displayed, can_undo=True)
    tree = _FakeTree(["r0", "r1"], ["r1", "r0"])

    state = HistoryMenuStateProvider(app).get_menu_state(tree)  # type: ignore[arg-type]

    assert state.has_selection is True
    assert state.selected_indices == (0, 1)
    assert state.selected_ids == [1.0, 2.0]
    assert state.first_selected_id == 1.0
    assert state.is_pinned is False
    assert state.can_undo is True


def test_menu_state_without_selection(app: MagicMock) -> None:
    _history_app(app, [("a", False, 1.0)], can_undo=False)
    state = HistoryMenuStateProvider(app).get_menu_state(_FakeTree(["r0"], []))  # type: ignore[arg-type]
    assert (state.has_selection, state.first_selected_id, state.can_undo) == (
        False,
        None,
        False,
    )


def test_history_menu_for_unpinned_selection(tk_root: tk.Tk, app: MagicMock) -> None:
    _history_app(app, [("a", False, 1.0)], can_undo=False)
    menu = HistoryContextMenu(tk_root, app)
    menu.tree = _FakeTree(["r0"], ["r0"])  # type: ignore[assignment]
    menu._build_dynamic_menu()

    assert _labels(menu.menu) == [
        "copy_selected",
        "open_as_quick_task",
        "format",
        "delete_selected",
        "-",
        "undo",
        "-",
        "pin",
    ]
    assert str(menu.menu.entrycget(0, "state")) == "normal"
    assert str(menu.menu.entrycget(5, "state")) == "disabled"  # undo 不可


def test_history_menu_without_selection_disables_actions(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    _history_app(app, [("a", False, 1.0)], can_undo=True)
    menu = HistoryContextMenu(tk_root, app)
    menu.tree = _FakeTree(["r0"], [])  # type: ignore[assignment]
    menu._build_dynamic_menu()
    assert str(menu.menu.entrycget(0, "state")) == "disabled"
    assert str(menu.menu.entrycget(5, "state")) == "normal"


@pytest.mark.parametrize(
    ("combo", "expected_labels"),
    [
        (None, ["unpin", "assign_hotkey"]),
        ("Ctrl+Shift+A", ["unpin", "change_hotkey", "remove_hotkey"]),
    ],
)
def test_history_menu_for_pinned_item_offers_hotkey_actions(
    tk_root: tk.Tk,
    app: MagicMock,
    combo: str | None,
    expected_labels: list[str],
) -> None:
    _history_app(app, [("a", True, 7.0)], can_undo=False)
    app.get_pinned_hotkey_combo.return_value = combo
    menu = HistoryContextMenu(tk_root, app)
    menu.tree = _FakeTree(["r0"], ["r0"])  # type: ignore[assignment]
    menu._build_dynamic_menu()
    assert _labels(menu.menu)[-len(expected_labels) :] == expected_labels

    # 追加された項目はそれぞれのアプリ操作を呼び出す
    menu.menu.invoke(len(_labels(menu.menu)) - len(expected_labels) + 1)
    app.open_pinned_hotkey_dialog.assert_called_once_with(7)
    if combo:
        menu.menu.invoke(menu.menu.index("end"))
        app.remove_pinned_hotkey_binding.assert_called_once_with(7)


def test_history_menu_commands_dispatch_events(tk_root: tk.Tk, app: MagicMock) -> None:
    _history_app(app, [("a", False, 1.0)], can_undo=True)
    menu = HistoryContextMenu(tk_root, app)
    menu.tree = _FakeTree(["r0"], ["r0"])  # type: ignore[assignment]
    menu._build_dynamic_menu()

    for index in (0, 1, 3, 5, 7):
        menu.menu.invoke(index)
    dispatched = [c.args for c in app.event_dispatcher.dispatch.call_args_list]
    assert dispatched == [
        ("HISTORY_COPY_SELECTED", [1.0]),
        ("HISTORY_CREATE_QUICK_TASK", [1.0]),
        ("HISTORY_DELETE_SELECTED", [1.0]),
        ("REQUEST_UNDO_LAST_ACTION",),
        ("HISTORY_PIN_UNPIN", 1.0),
    ]


def test_history_menu_show_selects_right_clicked_row(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    _history_app(app, [("a", False, 1.0), ("b", False, 2.0)], can_undo=False)
    menu = HistoryContextMenu(tk_root, app)
    tree = _FakeTree(["r0", "r1"], ["r0"])
    menu.tree = tree  # type: ignore[assignment]
    menu.menu.tk_popup = MagicMock()  # type: ignore[method-assign]
    event = SimpleNamespace(y=1, x_root=3, y_root=4)

    assert menu.show(event) == "break"  # type: ignore[arg-type]
    assert tree.selection() == ("r1",)
    assert tree.focused == "r1"
    menu.menu.tk_popup.assert_called_once_with(3, 4)


def test_history_menu_show_keeps_multi_selection_when_clicking_selected_row(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    _history_app(app, [("a", False, 1.0), ("b", False, 2.0)], can_undo=False)
    menu = HistoryContextMenu(tk_root, app)
    tree = _FakeTree(["r0", "r1"], ["r0", "r1"])
    menu.tree = tree  # type: ignore[assignment]
    menu.menu.tk_popup = MagicMock()  # type: ignore[method-assign]

    menu.show(SimpleNamespace(y=0, x_root=0, y_root=0))  # type: ignore[arg-type]
    assert tree.selection() == ("r0", "r1")


def test_history_menu_show_on_empty_area_keeps_selection(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    _history_app(app, [("a", False, 1.0)], can_undo=False)
    menu = HistoryContextMenu(tk_root, app)
    tree = _FakeTree(["r0"], ["r0"])
    menu.tree = tree  # type: ignore[assignment]
    menu.menu.tk_popup = MagicMock()  # type: ignore[method-assign]

    menu.show(SimpleNamespace(y=99, x_root=0, y_root=0))  # type: ignore[arg-type]
    assert tree.selection() == ("r0",)
    assert tree.focused is None


def test_history_menu_resolves_tree_from_application(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    _history_app(app, [], can_undo=False)
    menu = HistoryContextMenu(tk_root, app)
    assert menu._get_tree() is app.gui.history_component.tree
    menu._rebuild_menu()  # 動的メニューのため何もしない


class _SimpleMenu(BaseContextMenu):
    def build_menu(self) -> None:
        self.menu.add_command(label=self._translate("item"))


def test_base_menu_works_without_translator_and_dispatcher(tk_root: tk.Tk) -> None:
    menu = _SimpleMenu(tk_root)
    assert _labels(menu.menu) == ["item"]
    menu._dispatch("ANY_EVENT")  # ディスパッチャー未設定でも例外にならない
    menu._rebuild_menu()
    assert _labels(menu.menu) == ["item"]


def test_base_menu_rebuilds_when_language_changes(tk_root: tk.Tk) -> None:
    dispatcher = MagicMock()
    translations = {"item": "first"}
    menu = _SimpleMenu(tk_root, lambda key: translations[key], dispatcher)
    dispatcher.subscribe.assert_called_once_with("LANGUAGE_CHANGED", menu._rebuild_menu)
    translations["item"] = "second"
    menu._rebuild_menu()
    assert _labels(menu.menu) == ["second"]


def test_phrase_list_menu_selects_clicked_item_and_shows(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    listbox = tk.Listbox(tk_root)
    for text in ("a", "b", "c"):
        listbox.insert(tk.END, text)
    listbox.selection_set(0)
    list_component = SimpleNamespace(phrase_listbox=listbox)
    menu = PhraseListContextMenu(tk_root, app, list_component, MagicMock())  # type: ignore[arg-type]
    menu.menu.tk_popup = MagicMock()  # type: ignore[method-assign]
    listbox.nearest = lambda y: 2  # type: ignore[method-assign]

    assert menu.show(SimpleNamespace(y=0, x_root=1, y_root=2)) == "break"  # type: ignore[arg-type]
    assert listbox.curselection() == (2,)
    assert _labels(menu.menu) == ["copy", "add", "edit", "delete"]
    listbox.destroy()


def test_phrase_list_menu_tolerates_empty_listbox(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    listbox = MagicMock()
    listbox.nearest.side_effect = tk.TclError("empty")
    menu = PhraseListContextMenu(
        tk_root,
        app,
        SimpleNamespace(phrase_listbox=listbox),  # type: ignore[arg-type]
        MagicMock(),
    )
    menu.menu.tk_popup = MagicMock()  # type: ignore[method-assign]
    assert menu.show(SimpleNamespace(y=0, x_root=0, y_root=0)) == "break"  # type: ignore[arg-type]
