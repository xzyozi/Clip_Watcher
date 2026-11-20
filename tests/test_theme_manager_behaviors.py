"""ThemeManager のテーマ決定・ttk スタイル適用・ウィジェット着色のテスト。

実 Tk ではテーマの選択結果とウィジェットの色を、偽の Style では OS 別・
フォールバック経路を検証する。
"""

from __future__ import annotations

import sys
import tkinter as tk
from collections.abc import Generator
from tkinter import ttk
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.config.defaults import THEMES
from src.gui.theme_manager import ThemeManager


@pytest.fixture
def real_manager(tk_root: tk.Tk) -> Generator[ThemeManager, None, None]:
    """実 Tk に対するテーマ適用。後続のテストへ影響しないよう元のテーマへ戻す。"""
    style = ttk.Style(tk_root)
    original = style.theme_use()
    manager = ThemeManager(tk_root)
    yield manager
    manager.apply_theme("light")
    style.theme_use(original)


@pytest.fixture
def linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")


def _fake_style(
    theme_names: tuple[str, ...] = ("default", "clam", "aqua"),
    fail_on: str | None = None,
) -> MagicMock:
    """直近に選択されたテーマ名を返す偽の ttk.Style（fail_on の選択だけ TclError）。"""
    style = MagicMock()
    style.theme_names.return_value = theme_names
    used: list[str] = []

    def theme_use(name: str | None = None) -> str:
        if name is not None:
            if name == fail_on:
                raise tk.TclError(f"theme {name} is not available")
            used.append(name)
        return used[-1] if used else "default"

    style.theme_use.side_effect = theme_use
    return style


def _manager_with_fake_style(style: MagicMock) -> ThemeManager:
    manager = ThemeManager(MagicMock())
    manager.apply_theme_to_widget_tree = MagicMock()  # type: ignore[method-assign]
    patcher = patch("src.gui.theme_manager.ttk.Style", return_value=style)
    patcher.start()
    manager._patcher = patcher  # type: ignore[attr-defined]
    return manager


@pytest.fixture
def stop_patchers() -> Generator[list[ThemeManager], None, None]:
    created: list[ThemeManager] = []
    yield created
    for manager in created:
        manager._patcher.stop()  # type: ignore[attr-defined]


# --- 実 Tk でのテーマ適用 ---


def test_default_theme_is_light(tk_root: tk.Tk) -> None:
    assert ThemeManager(tk_root).get_current_theme() == "light"


@pytest.mark.usefixtures("linux")
def test_dark_theme_uses_clam_and_colors_widgets(
    tk_root: tk.Tk, real_manager: ThemeManager
) -> None:
    holder = tk.Toplevel(tk_root)
    entry = tk.Entry(holder)
    text = tk.Text(holder)
    entry.pack()
    text.pack()
    try:
        real_manager.apply_theme("dark")
        assert real_manager.get_current_theme() == "dark"
        assert ttk.Style(tk_root).theme_use() == "clam"
        assert str(entry.cget("bg")) == THEMES["dark"]["entry_bg"]
        assert str(text.cget("bg")) == THEMES["dark"]["listbox_bg"]
    finally:
        holder.destroy()


@pytest.mark.usefixtures("linux")
def test_light_theme_uses_default_and_selection_colors(
    tk_root: tk.Tk, real_manager: ThemeManager
) -> None:
    real_manager.apply_theme("light")
    style = ttk.Style(tk_root)
    assert style.theme_use() == "default"
    selected_bg = style.lookup("History.Treeview", "background", ["selected"])
    assert selected_bg == THEMES["light"]["select_bg"]


@pytest.mark.usefixtures("linux")
def test_unknown_theme_falls_back_to_light(real_manager: ThemeManager) -> None:
    real_manager.apply_theme("neon")
    assert real_manager.get_current_theme() == "light"


@pytest.mark.usefixtures("linux")
def test_apply_theme_notifies_icon_manager_and_styles_menubar(
    tk_root: tk.Tk, real_manager: ThemeManager
) -> None:
    icon_manager = MagicMock()
    real_manager.set_icon_manager(icon_manager)
    holder = tk.Toplevel(tk_root)
    menubar = tk.Menu(holder, tearoff=0)
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    menubar.add_command(label="Plain")
    real_manager.set_menubar(menubar)
    try:
        real_manager.apply_theme("dark")
        icon_manager.invalidate_theme.assert_called_once_with("dark")
        assert str(menubar.cget("background")) == THEMES["dark"]["menu_bg"]
        assert str(file_menu.cget("background")) == THEMES["dark"]["menu_bg"]
    finally:
        holder.destroy()


def test_apply_theme_to_toplevel_uses_current_theme(
    tk_root: tk.Tk, real_manager: ThemeManager
) -> None:
    real_manager.current_theme = "dark"
    window = tk.Toplevel(tk_root)
    try:
        real_manager.apply_theme_to_toplevel(window)
        assert str(window.cget("bg")) == THEMES["dark"]["bg"]
    finally:
        window.destroy()


def test_widget_tree_coloring_covers_each_widget_kind(
    tk_root: tk.Tk, real_manager: ThemeManager
) -> None:
    theme = THEMES["dark"]
    window = tk.Toplevel(tk_root)
    widgets: dict[str, Any] = {
        "frame": tk.Frame(window),
        "labelframe": tk.LabelFrame(window),
        "paned": tk.PanedWindow(window),
        "entry": tk.Entry(window),
        "text": tk.Text(window),
        "listbox": tk.Listbox(window),
        "button": tk.Button(window),
        "check": tk.Checkbutton(window),
        "radio": tk.Radiobutton(window),
        "label": tk.Label(window),
    }
    try:
        real_manager.apply_theme_to_widget_tree(window, theme)
        assert str(widgets["frame"].cget("bg")) == theme["bg"]
        assert str(widgets["labelframe"].cget("bg")) == theme["bg"]
        assert str(widgets["paned"].cget("bg")) == theme["frame_bg"]
        assert str(widgets["entry"].cget("bg")) == theme["entry_bg"]
        assert str(widgets["text"].cget("fg")) == theme["listbox_fg"]
        assert str(widgets["listbox"].cget("bg")) == theme["listbox_bg"]
        assert str(widgets["button"].cget("bg")) == theme["button_bg"]
        assert str(widgets["check"].cget("selectcolor")) == theme["frame_bg"]
        assert str(widgets["radio"].cget("bg")) == theme["button_bg"]
        assert str(widgets["label"].cget("fg")) == theme["label_fg"]
    finally:
        window.destroy()


def test_widget_tree_coloring_ignores_unsupported_options() -> None:
    manager = ThemeManager(MagicMock())
    broken = MagicMock(spec=tk.Frame)
    broken.config.side_effect = tk.TclError("unsupported")
    broken.winfo_children.return_value = []
    manager.apply_theme_to_widget_tree(broken, THEMES["light"])  # 例外を送出しない


def test_menu_theming_tolerates_failures() -> None:
    manager = ThemeManager(MagicMock())
    menu = MagicMock()
    menu.config.side_effect = tk.TclError("cannot configure")
    menu.index.side_effect = tk.TclError("torn off")
    manager._apply_theme_to_menu(menu, THEMES["light"])  # 例外を送出しない

    menu = MagicMock()
    menu.index.return_value = None
    manager._apply_theme_to_menu(menu, THEMES["light"])
    menu.type.assert_not_called()


# --- OS 別・フォールバック（偽の Style） ---


def test_clam_unavailable_falls_back_to_default(
    stop_patchers: list[ThemeManager], linux: None
) -> None:
    style = _fake_style(fail_on="clam")
    manager = _manager_with_fake_style(style)
    stop_patchers.append(manager)
    manager.apply_theme("dark")
    assert manager.get_current_theme() == "dark"
    style.theme_use.assert_any_call("default")


def test_dark_selection_workaround_falls_back_when_empty_map_fails(
    stop_patchers: list[ThemeManager], linux: None
) -> None:
    style = _fake_style()

    def fake_map(name: str, **options: Any) -> None:
        if options.get("background") == []:
            raise tk.TclError("cannot clear map")

    style.map.side_effect = fake_map
    manager = _manager_with_fake_style(style)
    stop_patchers.append(manager)
    manager.apply_theme("dark")
    selected_maps = [
        c for c in style.map.call_args_list if c.args[0] == "History.Treeview"
    ]
    assert selected_maps[-1].kwargs["background"] == [
        ("selected", THEMES["dark"]["select_bg"])
    ]


def test_macos_forces_light_on_legacy_tk(
    stop_patchers: list[ThemeManager], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(tk, "TkVersion", 8.5)
    style = _fake_style()
    manager = _manager_with_fake_style(style)
    stop_patchers.append(manager)
    manager.apply_theme("dark")
    assert manager.get_current_theme() == "light"
    style.theme_use.assert_any_call("aqua")


@pytest.mark.parametrize(("is_dark", "expected"), [(True, "dark"), (False, "light")])
def test_macos_follows_system_appearance(
    stop_patchers: list[ThemeManager],
    monkeypatch: pytest.MonkeyPatch,
    is_dark: bool,
    expected: str,
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(tk, "TkVersion", 8.6)
    monkeypatch.setattr("src.utils.platform_utils.is_macos_dark_mode", lambda: is_dark)
    style = _fake_style()
    manager = _manager_with_fake_style(style)
    stop_patchers.append(manager)
    manager.apply_theme("light")
    assert manager.get_current_theme() == expected
    treeview_maps = [
        c for c in style.map.call_args_list if c.args[0] == "History.Treeview"
    ]
    assert treeview_maps[-1].kwargs["background"] == [("selected", "systemHighlight")]


def test_macos_falls_back_to_default_when_aqua_fails(
    stop_patchers: list[ThemeManager], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(tk, "TkVersion", 8.6)
    monkeypatch.setattr("src.utils.platform_utils.is_macos_dark_mode", lambda: False)
    style = _fake_style(fail_on="aqua")
    manager = _manager_with_fake_style(style)
    stop_patchers.append(manager)
    manager.apply_theme("light")
    style.theme_use.assert_any_call("default")
