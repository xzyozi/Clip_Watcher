from __future__ import annotations

from unittest.mock import Mock, patch

from src.event_handlers.history_handlers import HistoryEventHandlers


def make_handler(*, warning_enabled: bool) -> HistoryEventHandlers:
    handler = HistoryEventHandlers.__new__(HistoryEventHandlers)
    handler.app = Mock()
    handler.app.settings_manager.get_setting.return_value = warning_enabled
    handler.app.monitor.get_history.return_value = [
        ("sudo rm -rf ./build", False, 1.0),
        ("safe text", False, 2.0),
    ]
    return handler


def test_copy_warning_cancel_keeps_clipboard_unchanged() -> None:
    handler = make_handler(warning_enabled=True)

    with patch(
        "src.event_handlers.history_handlers.messagebox.askyesno",
        return_value=False,
    ) as askyesno:
        handler.handle_copy_selected_history([1.0])

    askyesno.assert_called_once()
    handler.app.master.clipboard_clear.assert_not_called()
    handler.app.master.clipboard_append.assert_not_called()


def test_copy_warning_is_disabled_by_default_behavior() -> None:
    handler = make_handler(warning_enabled=False)

    with patch("src.event_handlers.history_handlers.messagebox.askyesno") as askyesno:
        handler.handle_copy_selected_history([1.0])

    askyesno.assert_not_called()
    handler.app.master.clipboard_clear.assert_called_once()
    handler.app.master.clipboard_append.assert_called_once_with("sudo rm -rf ./build")


def test_copy_warning_applies_to_merged_content() -> None:
    handler = make_handler(warning_enabled=True)

    with patch(
        "src.event_handlers.history_handlers.messagebox.askyesno",
        return_value=True,
    ) as askyesno:
        handler.handle_copy_selected_as_merged([1.0, 2.0])

    askyesno.assert_called_once()
    handler.app.master.clipboard_clear.assert_called_once()
    handler.app.master.clipboard_append.assert_called_once_with(
        "sudo rm -rf ./build\nsafe text"
    )
