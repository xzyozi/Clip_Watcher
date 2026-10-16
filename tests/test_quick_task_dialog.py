"""tests/test_quick_task_dialog.py

QuickTaskDialog のコピー処理が、クリップボード監視レイヤー経由で行われることを検証する。
Tk の実ウィンドウは生成せず、``_copy_selected`` を偽の self で呼び出す。
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.gui.windows.quick_task_dialog import QuickTaskDialog


def _dialog(selection: tuple[str, ...], delete_on_copy: bool) -> MagicMock:
    dialog = MagicMock()
    dialog.task_list.selection.return_value = selection
    dialog.task_list.item.return_value = {"values": ["task A"]}
    dialog.delete_on_copy.get.return_value = delete_on_copy
    return dialog


def test_copy_selected_uses_monitor_update_clipboard() -> None:
    dialog = _dialog(("I001",), delete_on_copy=False)
    dialog.task_list.get_children.return_value = ("I001",)

    QuickTaskDialog._copy_selected(dialog)

    dialog.app.monitor.update_clipboard.assert_called_once_with("task A")
    dialog.clipboard_clear.assert_not_called()
    dialog.clipboard_append.assert_not_called()
    dialog.task_list.delete.assert_not_called()


def test_copy_selected_without_selection_does_nothing() -> None:
    dialog = _dialog((), delete_on_copy=False)

    QuickTaskDialog._copy_selected(dialog)

    dialog.app.monitor.update_clipboard.assert_not_called()


def test_copy_selected_deletes_item_and_closes_when_last_task_removed() -> None:
    dialog = _dialog(("I001",), delete_on_copy=True)
    dialog.task_list.get_children.return_value = ()

    QuickTaskDialog._copy_selected(dialog)

    dialog.app.monitor.update_clipboard.assert_called_once_with("task A")
    dialog.task_list.delete.assert_called_once_with("I001")
    dialog.destroy.assert_called_once()
