"""メタ管理画面（カテゴリ/定型文の編集ダイアログとメインフレーム）のテスト。

実 Tk と実 SQLite を使い、モーダルダイアログ（wait_window / grab_set）と
メッセージボックスだけを差し替える。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.db.database_manager import DatabaseManager
from src.db.dto import CategoryDTO, MetaPhraseDTO
from src.gui.windows import meta_management_window as window
from src.gui.windows.meta_management_window import (
    CategoryEditDialog,
    MetaManagementFrame,
    MetaPhraseEditDialog,
)

MODULE = "src.gui.windows.meta_management_window"


@pytest.fixture(autouse=True)
def _no_grab(monkeypatch: pytest.MonkeyPatch) -> None:
    """表示前のウィンドウでは grab_set が失敗する環境があるため無効化する。"""
    monkeypatch.setattr(tk.Toplevel, "grab_set", lambda self: None)


@pytest.fixture
def app(tmp_path: Path) -> MagicMock:
    app = MagicMock()
    app.translator = lambda key: key
    app.db_manager = DatabaseManager(db_path=str(tmp_path / "meta.db"))
    app.theme_manager = MagicMock(
        spec=["get_current_theme", "apply_theme_to_widget_tree"]
    )
    app.theme_manager.get_current_theme.return_value = "light"
    return app


# --- CategoryEditDialog ---


@pytest.fixture
def category_dialog(
    tk_root: tk.Tk, app: MagicMock
) -> Generator[CategoryEditDialog, None, None]:
    dialog = CategoryEditDialog(tk_root, app)
    yield dialog
    if dialog.winfo_exists():
        dialog.destroy()


def test_category_dialog_accepts_new_name(category_dialog: CategoryEditDialog) -> None:
    category_dialog.entry.insert(0, "  Work  ")
    category_dialog.on_ok()
    assert category_dialog.result == "Work"


def test_category_dialog_rejects_blank_name(
    category_dialog: CategoryEditDialog,
) -> None:
    with patch(f"{MODULE}.messagebox") as box:
        category_dialog.on_ok()
    box.showerror.assert_called_once()
    assert category_dialog.result is None


def test_category_dialog_rejects_duplicate_name_case_insensitively(
    app: MagicMock, category_dialog: CategoryEditDialog
) -> None:
    app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    category_dialog.entry.insert(0, "wORK")
    with patch(f"{MODULE}.messagebox") as box:
        category_dialog.on_ok()
    box.showerror.assert_called_once()
    assert category_dialog.result is None


def test_category_dialog_edit_allows_keeping_own_name(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    category_id = app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    dto = CategoryDTO(name="Work", id=category_id)
    dialog = CategoryEditDialog(tk_root, app, dto)
    try:
        assert dialog.entry.get() == "Work"
        dialog.on_ok()
        assert dialog.result == "Work"
    finally:
        if dialog.winfo_exists():
            dialog.destroy()


def test_category_dialog_reports_unexpected_errors(
    app: MagicMock, category_dialog: CategoryEditDialog
) -> None:
    category_dialog.entry.insert(0, "Work")
    app.db_manager = MagicMock()
    app.db_manager.category_dao.get_all.side_effect = RuntimeError("boom")
    with patch(f"{MODULE}.log_and_show_error") as report:
        category_dialog.on_ok()
    report.assert_called_once()


# --- MetaPhraseEditDialog ---


@pytest.fixture
def two_categories(app: MagicMock) -> tuple[int, int]:
    dao = app.db_manager.category_dao
    return dao.add(CategoryDTO(name="Work")), dao.add(CategoryDTO(name="Home"))


def _open_phrase_dialog(
    tk_root: tk.Tk, app: MagicMock, **kwargs: Any
) -> MetaPhraseEditDialog:
    return MetaPhraseEditDialog(tk_root, app, **kwargs)


def test_phrase_dialog_preselects_first_category_by_default(
    tk_root: tk.Tk, app: MagicMock, two_categories: tuple[int, int]
) -> None:
    dialog = _open_phrase_dialog(tk_root, app)
    try:
        assert dialog.cat_combobox.current() == 0
    finally:
        dialog.destroy()


def test_phrase_dialog_preselects_default_category(
    tk_root: tk.Tk, app: MagicMock, two_categories: tuple[int, int]
) -> None:
    dialog = _open_phrase_dialog(tk_root, app, default_category_id=two_categories[1])
    try:
        assert dialog.cat_combobox.current() == 1
    finally:
        dialog.destroy()


def test_phrase_dialog_loads_existing_phrase(
    tk_root: tk.Tk, app: MagicMock, two_categories: tuple[int, int]
) -> None:
    phrase = MetaPhraseDTO("greet", "Hello", two_categories[1])
    dialog = _open_phrase_dialog(tk_root, app, phrase_dto=phrase)
    try:
        assert dialog.title_entry.get() == "greet"
        assert dialog.content_text.get("1.0", "end-1c") == "Hello"
        assert dialog.cat_combobox.current() == 1
    finally:
        dialog.destroy()


def test_phrase_dialog_returns_title_content_and_category(
    tk_root: tk.Tk, app: MagicMock, two_categories: tuple[int, int]
) -> None:
    dialog = _open_phrase_dialog(tk_root, app, default_category_id=two_categories[0])
    dialog.title_entry.insert(0, " greet ")
    dialog.content_text.insert("1.0", "  Hello  ")
    dialog.on_ok()
    assert dialog.result == ("greet", "Hello", two_categories[0])


def test_phrase_dialog_requires_content(
    tk_root: tk.Tk, app: MagicMock, two_categories: tuple[int, int]
) -> None:
    dialog = _open_phrase_dialog(tk_root, app)
    try:
        with patch(f"{MODULE}.messagebox") as box:
            dialog.on_ok()
        box.showerror.assert_called_once()
        assert dialog.result is None
    finally:
        dialog.destroy()


def test_phrase_dialog_requires_category_selection(
    tk_root: tk.Tk, app: MagicMock
) -> None:
    dialog = _open_phrase_dialog(tk_root, app)  # カテゴリが1件もない
    try:
        dialog.content_text.insert("1.0", "Hello")
        with patch(f"{MODULE}.messagebox") as box:
            dialog.on_ok()
        box.showerror.assert_called_once()
        assert dialog.result is None
    finally:
        dialog.destroy()


def test_phrase_dialog_reports_unexpected_errors(
    tk_root: tk.Tk, app: MagicMock, two_categories: tuple[int, int]
) -> None:
    dialog = _open_phrase_dialog(tk_root, app)
    try:
        dialog.content_text.insert("1.0", "Hello")
        dialog.categories = []  # 添字エラーを起こす
        with patch(f"{MODULE}.log_and_show_error") as report:
            dialog.on_ok()
        report.assert_called_once()
    finally:
        dialog.destroy()


# --- MetaManagementFrame ---


@pytest.fixture
def frame(tk_root: tk.Tk, app: MagicMock) -> Generator[MetaManagementFrame, None, None]:
    meta = MetaManagementFrame(tk_root, app)
    meta.pack()
    # モーダル待機はテストでは行わない
    meta.wait_window = MagicMock()  # type: ignore[method-assign]
    yield meta
    meta.destroy()


def _fake_dialog(result: Any) -> MagicMock:
    """ダイアログクラスの代わりに、結果だけを持つオブジェクトを返すファクトリ。"""
    return MagicMock(return_value=SimpleNamespace(result=result))


def _select_category(frame: MetaManagementFrame, index: int) -> None:
    frame.cat_listbox.selection_clear(0, tk.END)
    frame.cat_listbox.selection_set(index)
    frame.on_category_select()


def test_frame_lists_all_item_and_categories(app: MagicMock, tk_root: tk.Tk) -> None:
    app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    meta = MetaManagementFrame(tk_root, app)
    try:
        items = [meta.cat_listbox.get(i) for i in range(meta.cat_listbox.size())]
        assert items == ["  all_categories", "  Work"]
        assert meta.cat_listbox.curselection() == (0,)
    finally:
        meta.destroy()


def test_frame_add_category_via_dialog(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    with patch(f"{MODULE}.CategoryEditDialog", _fake_dialog("Work")):
        frame.add_category()
    assert [c.name for c in app.db_manager.category_dao.get_all()] == ["Work"]
    assert frame.cat_listbox.size() == 2


def test_frame_add_category_cancelled(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    with patch(f"{MODULE}.CategoryEditDialog", _fake_dialog(None)):
        frame.add_category()
    assert app.db_manager.category_dao.get_all() == []


def test_frame_edit_category(app: MagicMock, frame: MetaManagementFrame) -> None:
    app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    frame.refresh_categories()

    # 「すべて」選択中は編集できない
    with patch(f"{MODULE}.CategoryEditDialog", _fake_dialog("X")) as dialog_cls:
        frame.edit_category()
    dialog_cls.assert_not_called()

    _select_category(frame, 1)
    with patch(f"{MODULE}.CategoryEditDialog", _fake_dialog("Office")):
        frame.edit_category()
    assert [c.name for c in app.db_manager.category_dao.get_all()] == ["Office"]


def test_frame_delete_category_without_phrases(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    frame.refresh_categories()

    frame.delete_category()  # 「すべて」選択中は何もしない
    assert len(app.db_manager.category_dao.get_all()) == 1

    _select_category(frame, 1)
    frame.delete_category()
    assert app.db_manager.category_dao.get_all() == []
    assert frame.selected_category_id is None


@pytest.mark.parametrize("confirmed", [True, False])
def test_frame_delete_category_with_phrases_asks_confirmation(
    app: MagicMock, frame: MetaManagementFrame, confirmed: bool
) -> None:
    category_id = app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    app.db_manager.meta_phrase_dao.add(MetaPhraseDTO("t", "c", category_id))
    frame.refresh_categories()
    _select_category(frame, 1)

    with patch(f"{MODULE}.messagebox.askyesno", return_value=confirmed) as ask:
        frame.delete_category()
    ask.assert_called_once()
    remaining = app.db_manager.category_dao.get_all()
    assert (remaining == []) is confirmed


def test_frame_filters_phrases_by_selected_category(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    dao = app.db_manager
    work = dao.category_dao.add(CategoryDTO(name="Work"))
    home = dao.category_dao.add(CategoryDTO(name="Home"))
    dao.meta_phrase_dao.add(MetaPhraseDTO("greet", "Hello\nWorld", work))
    dao.meta_phrase_dao.add(MetaPhraseDTO("", "No title", home))
    frame.refresh_categories()

    assert len(frame.phrase_tree.get_children()) == 2  # すべて
    _select_category(frame, 1)
    rows = [
        frame.phrase_tree.item(i, "values") for i in frame.phrase_tree.get_children()
    ]
    assert rows == [("greet", "Hello World")]
    _select_category(frame, 2)
    rows = [
        frame.phrase_tree.item(i, "values") for i in frame.phrase_tree.get_children()
    ]
    assert rows == [("no_title", "No title")]


def test_frame_restores_selected_category_after_refresh(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    frame.refresh_categories()
    _select_category(frame, 1)
    frame.refresh_categories()
    assert frame.cat_listbox.curselection() == (1,)

    frame.selected_category_id = 9999  # 存在しないカテゴリは「すべて」に戻す
    frame.refresh_categories()
    assert frame.selected_category_id is None
    assert frame.cat_listbox.curselection() == (0,)


def test_frame_category_select_without_selection_is_ignored(
    frame: MetaManagementFrame,
) -> None:
    frame.cat_listbox.selection_clear(0, tk.END)
    frame.on_category_select()  # 例外を送出しない


def test_frame_add_phrase_requires_a_category(
    frame: MetaManagementFrame,
) -> None:
    with patch(f"{MODULE}.messagebox") as box:
        frame.add_phrase()
    box.showerror.assert_called_once()


def test_frame_add_edit_and_delete_phrase(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    category_id = app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    frame.refresh_categories()

    with patch(f"{MODULE}.MetaPhraseEditDialog", _fake_dialog(("t", "c", category_id))):
        frame.add_phrase()
    phrases = app.db_manager.meta_phrase_dao.get_by_category()
    assert [(p.title, p.content) for p in phrases] == [("t", "c")]

    row = frame.phrase_tree.get_children()[0]
    frame.phrase_tree.selection_set(row)
    with patch(
        f"{MODULE}.MetaPhraseEditDialog", _fake_dialog(("t2", "c2", category_id))
    ):
        frame.edit_phrase()
    phrases = app.db_manager.meta_phrase_dao.get_by_category()
    assert [(p.title, p.content) for p in phrases] == [("t2", "c2")]

    frame.phrase_tree.selection_set(frame.phrase_tree.get_children()[0])
    frame.delete_phrase()
    assert app.db_manager.meta_phrase_dao.get_by_category() == []


def test_frame_phrase_actions_without_selection_do_nothing(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    frame.edit_phrase()
    frame.delete_phrase()
    frame.copy_selected_phrase()
    app.monitor.update_clipboard.assert_not_called()


def test_frame_edit_phrase_ignores_unknown_row(
    frame: MetaManagementFrame,
) -> None:
    frame.phrase_tree.insert("", tk.END, iid="999", values=("a", "b"))
    frame.phrase_tree.selection_set("999")
    with patch(f"{MODULE}.MetaPhraseEditDialog") as dialog_cls:
        frame.edit_phrase()
    dialog_cls.assert_not_called()


def test_frame_copy_phrase_updates_clipboard_and_double_click_copies(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    category_id = app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    app.db_manager.meta_phrase_dao.add(MetaPhraseDTO("t", "Body", category_id))
    frame.refresh_categories()
    frame.phrase_tree.selection_set(frame.phrase_tree.get_children()[0])

    frame.copy_selected_phrase()
    frame.on_phrase_double_click(MagicMock())
    assert app.monitor.update_clipboard.call_count == 2
    app.monitor.update_clipboard.assert_called_with("Body")


def _click_event(y: int = 5) -> SimpleNamespace:
    return SimpleNamespace(y=y, x_root=10, y_root=20)


def test_frame_context_menu_on_category_enables_edit_items(
    app: MagicMock, frame: MetaManagementFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    app.db_manager.category_dao.add(CategoryDTO(name="Work"))
    frame.refresh_categories()
    monkeypatch.setattr(frame.cat_listbox, "nearest", lambda y: 1)
    monkeypatch.setattr(frame.cat_listbox, "bbox", lambda i: (0, 0, 100, 20))
    popup = MagicMock()
    monkeypatch.setattr(frame.cat_menu, "tk_popup", popup)

    assert frame.show_context_menu(_click_event()) == "break"  # type: ignore[arg-type]
    popup.assert_called_once_with(10, 20)
    assert frame.cat_menu.entrycget(1, "state") == "normal"
    assert frame.selected_category_id is not None


def test_frame_context_menu_on_all_item_disables_edit_items(
    frame: MetaManagementFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(frame.cat_listbox, "nearest", lambda y: 0)
    monkeypatch.setattr(frame.cat_listbox, "bbox", lambda i: (0, 0, 100, 20))
    monkeypatch.setattr(frame.cat_menu, "tk_popup", MagicMock())

    frame.show_context_menu(_click_event())  # type: ignore[arg-type]
    assert frame.cat_menu.entrycget(1, "state") == "disabled"


def test_frame_context_menu_outside_items_keeps_selection(
    frame: MetaManagementFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(frame.cat_listbox, "nearest", lambda y: 0)
    monkeypatch.setattr(frame.cat_listbox, "bbox", lambda i: None)
    monkeypatch.setattr(frame.cat_menu, "tk_popup", MagicMock())
    frame.show_context_menu(_click_event(y=500))  # type: ignore[arg-type]
    assert frame.cat_menu.entrycget(1, "state") == "disabled"


def test_frame_context_menu_reports_errors(
    frame: MetaManagementFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        frame.cat_listbox, "nearest", MagicMock(side_effect=RuntimeError("boom"))
    )
    frame.log_and_show_error = MagicMock()  # type: ignore[method-assign]
    assert frame.show_context_menu(_click_event()) is None  # type: ignore[arg-type]
    frame.log_and_show_error.assert_called_once()


def test_frame_language_change_updates_labels(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    app.translator = lambda key: f"T:{key}"
    frame.on_language_changed()
    assert frame.category_label.cget("text") == "T:meta_category_title"
    assert frame.copy_phrase_btn.cget("text") == "T:copy"


def test_frame_operations_report_unexpected_errors(
    app: MagicMock, frame: MetaManagementFrame
) -> None:
    app.db_manager = MagicMock()
    app.db_manager.category_dao.get_all.side_effect = RuntimeError("boom")
    app.db_manager.category_dao.get_meta_phrase_count.side_effect = RuntimeError("x")
    app.db_manager.meta_phrase_dao.get_by_category.side_effect = RuntimeError("boom")
    frame.log_and_show_error = MagicMock()  # type: ignore[method-assign]

    frame.refresh_categories()
    frame.refresh_phrases()
    assert frame.log_and_show_error.call_count >= 2

    frame.log_and_show_error.reset_mock()
    frame.category_list = [CategoryDTO(name="Work", id=1)]
    frame.cat_listbox.insert(tk.END, "  Work")
    _select_category(frame, 1)
    frame.delete_category()
    frame.log_and_show_error.assert_called()


def test_frame_dialog_errors_are_reported(frame: MetaManagementFrame) -> None:
    frame.log_and_show_error = MagicMock()  # type: ignore[method-assign]
    boom = MagicMock(side_effect=RuntimeError("boom"))
    frame.category_list = [CategoryDTO(name="Work", id=1)]
    frame.cat_listbox.insert(tk.END, "  Work")
    _select_category(frame, 1)

    with patch(f"{MODULE}.CategoryEditDialog", boom):
        frame.add_category()
        frame.edit_category()
    with patch(f"{MODULE}.MetaPhraseEditDialog", boom):
        frame.add_phrase()
    assert frame.log_and_show_error.call_count == 3


def test_module_exposes_dialog_classes() -> None:
    assert window.CategoryEditDialog is CategoryEditDialog
    assert window.MetaPhraseEditDialog is MetaPhraseEditDialog
