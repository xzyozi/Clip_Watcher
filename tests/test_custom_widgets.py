"""tests/test_custom_widgets.py

ContextMenuMixin が app インスタンスに依存せず、translator と言語変更通知の
注入だけで動作することを検証する (#143)。Tk の実ウィンドウは生成しない。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.gui.custom_widgets import (
    LANGUAGE_CHANGED_EVENT,
    ContextMenuMixin,
    CustomEntry,
    _fallback_translator,
)


def _construct(**kwargs: object) -> tuple[CustomEntry, MagicMock]:
    """tk.Entry の実体化をスタブして CustomEntry を生成する。"""
    menu = MagicMock()
    with (
        patch("tkinter.Entry.__init__", return_value=None),
        patch("src.gui.custom_widgets.tk.Menu", return_value=menu),
        patch.object(CustomEntry, "bind"),
    ):
        widget = CustomEntry(MagicMock(), **kwargs)
    return widget, menu


def test_works_without_app_using_fallback_translator() -> None:
    widget, menu = _construct()

    labels = [c.kwargs["label"] for c in menu.add_command.call_args_list]
    assert labels == ["Cut", "Copy", "Paste", "Select All"]
    assert widget.translator is _fallback_translator


def test_uses_injected_translator() -> None:
    translator = MagicMock(side_effect=lambda key: f"T:{key}")

    _, menu = _construct(translator=translator)

    labels = [c.kwargs["label"] for c in menu.add_command.call_args_list]
    assert labels == ["T:cut", "T:copy", "T:paste", "T:select_all"]


def test_subscribes_to_language_events_when_provided() -> None:
    notifier = MagicMock()

    widget, _ = _construct(language_events=notifier)

    notifier.subscribe.assert_called_once_with(
        LANGUAGE_CHANGED_EVENT, widget._rebuild_menu
    )


def test_does_not_require_language_events() -> None:
    widget, _ = _construct()

    assert widget._language_events is None


def test_unsubscribes_on_destroy_of_the_widget_only() -> None:
    notifier = MagicMock()
    widget, _ = _construct(language_events=notifier)

    widget._on_destroy(MagicMock(widget=object()))
    notifier.unsubscribe.assert_not_called()

    widget._on_destroy(MagicMock(widget=widget))
    notifier.unsubscribe.assert_called_once_with(
        LANGUAGE_CHANGED_EVENT, widget._rebuild_menu
    )


def test_rebuild_menu_recreates_entries() -> None:
    widget, menu = _construct()
    menu.reset_mock()

    widget._rebuild_menu()

    menu.delete.assert_called_once()
    assert menu.add_command.call_count == 4


def test_mixin_has_no_app_attribute_contract() -> None:
    assert "app" not in ContextMenuMixin.__init__.__code__.co_varnames


def test_bind_context_menu_on_darwin() -> None:
    """macOS (darwin) では Button-2, Button-3, Control-Button-1 がバインドされること。"""
    from src.gui.custom_widgets import bind_context_menu

    widget = MagicMock()
    callback = MagicMock()

    with patch("sys.platform", "darwin"):
        bind_context_menu(widget, callback)

    bound_events = [c.args[0] for c in widget.bind.call_args_list]
    assert "<Button-2>" in bound_events
    assert "<Button-3>" in bound_events
    assert "<Control-Button-1>" in bound_events
    for c in widget.bind.call_args_list:
        assert c.kwargs.get("add") == "+"
        assert c.args[1] is callback


def test_bind_context_menu_on_non_darwin() -> None:
    """非 macOS (win32, linux) では Button-3 のみがバインドされること。"""
    from src.gui.custom_widgets import bind_context_menu

    widget_win = MagicMock()
    callback = MagicMock()

    with patch("sys.platform", "win32"):
        bind_context_menu(widget_win, callback)

    bound_events_win = [c.args[0] for c in widget_win.bind.call_args_list]
    assert bound_events_win == ["<Button-3>"]

    widget_linux = MagicMock()
    with patch("sys.platform", "linux"):
        bind_context_menu(widget_linux, callback)

    bound_events_linux = [c.args[0] for c in widget_linux.bind.call_args_list]
    assert bound_events_linux == ["<Button-3>"]


def test_show_context_menu_returns_break() -> None:
    """show_context_menu は後続のデフォルト動作を抑制するために 'break' を返すこと。"""
    widget, menu = _construct()
    event = MagicMock()
    event.x_root = 100
    event.y_root = 150

    result = widget.show_context_menu(event)

    menu.tk_popup.assert_called_once_with(100, 150)
    assert result == "break"
