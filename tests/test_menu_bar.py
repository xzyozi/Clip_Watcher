"""tests/test_menu_bar.py

MenuBar が UI 状態を自身で保持し、アプリケーションインスタンスへ属性を
注入しないこと、選択履歴の取得がファサード経由であることを検証する (#140)。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.gui.menu_bar import MenuBar


class _Var:
    """tk.BooleanVar / tk.StringVar の代替（Tk ルート不要）。"""

    def __init__(self, value: object = None) -> None:
        self._value = value

    def get(self) -> object:
        return self._value

    def set(self, value: object) -> None:
        self._value = value


@pytest.fixture
def created_menus() -> Iterator[list[MagicMock]]:
    """Tk の実体化を避けるため、変数とメニューをスタブし、生成メニューを記録する。"""
    menus: list[MagicMock] = []

    def _menu_factory(*args: Any, **kwargs: Any) -> MagicMock:
        menu = MagicMock()
        menus.append(menu)
        return menu

    with (
        patch("src.gui.menu_bar.tk.BooleanVar", _Var),
        patch("src.gui.menu_bar.tk.StringVar", _Var),
        patch("src.gui.menu_bar.tk.Menu", side_effect=_menu_factory),
    ):
        yield menus


@pytest.fixture
def app() -> MagicMock:
    app = MagicMock(
        spec=[
            "settings_manager",
            "translator",
            "plugin_manager",
            "gui",
            "event_dispatcher",
            "history_handlers",
            "file_handlers",
            "settings_handlers",
            "reassert_topmost",
            "open_settings_window",
        ]
    )
    app.settings_manager.get_setting.side_effect = lambda key, default=None: {
        "always_on_top": True,
        "theme": "dark",
    }.get(key, default)
    app.translator = lambda key: key
    app.plugin_manager.get_gui_plugins.return_value = []
    app.gui = MagicMock(spec=["get_selected_history_ids", "select_tool_tab"])
    return app


def _command_for(menus: list[MagicMock], label: str) -> Callable[[], None]:
    for menu in menus:
        for call in menu.add_command.call_args_list:
            if call.kwargs.get("label") == label:
                return call.kwargs["command"]  # type: ignore[no-any-return]
    raise AssertionError(f"menu item not found: {label}")


def test_menu_bar_keeps_ui_state_and_does_not_inject_into_app(
    app: MagicMock, created_menus: list[MagicMock]
) -> None:
    menu_bar = MenuBar(MagicMock(), app)

    assert menu_bar.always_on_top_var.get() is True
    assert menu_bar.theme_var.get() == "dark"
    assert not hasattr(app, "always_on_top_var")
    assert not hasattr(app, "theme_var")


def test_sync_settings_updates_menu_state(
    app: MagicMock, created_menus: list[MagicMock]
) -> None:
    menu_bar = MenuBar(MagicMock(), app)

    menu_bar.sync_settings("light", False)

    assert menu_bar.theme_var.get() == "light"
    assert menu_bar.always_on_top_var.get() is False


def test_copy_merged_uses_gui_facade_for_selected_ids(
    app: MagicMock, created_menus: list[MagicMock]
) -> None:
    app.gui.get_selected_history_ids.return_value = [1.0, 2.0]
    MenuBar(MagicMock(), app)

    _command_for(created_menus, "copy_merged_menu_item")()

    app.event_dispatcher.dispatch.assert_called_once_with(
        "HISTORY_COPY_MERGED", [1.0, 2.0]
    )


def test_delete_selected_uses_gui_facade_for_selected_ids(
    app: MagicMock, created_menus: list[MagicMock]
) -> None:
    app.gui.get_selected_history_ids.return_value = [3.0]
    MenuBar(MagicMock(), app)

    _command_for(created_menus, "delete_selected_menu_item")()

    app.history_handlers.handle_delete_selected_history.assert_called_once_with([3.0])
