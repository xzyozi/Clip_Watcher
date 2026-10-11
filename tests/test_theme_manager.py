from __future__ import annotations

import sys
import tkinter as tk
from tkinter import Tk
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from src.core.config.defaults import THEMES
from src.gui.icon_manager import IconManager
from src.gui.theme_manager import ThemeManager


class HeadlessStyle:
    """Tkの表示サーバーなしでテーマ適用を検証するための最小限のStyle代替。"""

    last_instance: HeadlessStyle | None = None
    _available_themes: tuple[str, ...] = ("default", "clam", "alt", "classic")

    def __init__(self, root: Tk) -> None:
        self.root = root
        self.configurations: list[tuple[str, dict[str, object]]] = []
        self.used_themes: list[str] = []
        HeadlessStyle.last_instance = self

    def theme_names(self) -> tuple[str, ...]:
        return self._available_themes

    def theme_use(self, theme_name: str | None = None) -> str | None:
        if theme_name is not None:
            self.used_themes.append(theme_name)
        return self.used_themes[-1] if self.used_themes else "default"

    def configure(self, style_name: str, **options: object) -> None:
        self.configurations.append((style_name, options))

    def map(self, style_name: str, **options: object) -> None:
        pass


def configure_headless_theme_application(
    monkeypatch: object, theme_manager: ThemeManager
) -> None:
    """アイコン連携以外のGUIスタイル適用を無害化する。"""
    monkeypatch.setattr("src.gui.theme_manager.ttk.Style", HeadlessStyle)
    theme_manager.apply_theme_to_widget_tree = lambda widget, theme: None


def test_set_icon_manager_keeps_the_registered_instance() -> None:
    """要件3.2: 登録したIconManagerをテーマ切替用に保持する。"""
    theme_manager = ThemeManager(cast(Tk, object()))
    icon_manager = IconManager()

    assert theme_manager.icon_manager is None

    theme_manager.set_icon_manager(icon_manager)

    assert theme_manager.icon_manager is icon_manager


def test_apply_theme_invalidates_registered_icon_cache_with_fallback_theme(
    monkeypatch: object,
) -> None:
    """要件3.2: 登録済みIconManagerへ有効な切替先テーマを通知する。"""
    theme_manager = ThemeManager(cast(Tk, object()))
    icon_manager = IconManager()
    icon_manager._icon_cache["pin:light"] = object()
    theme_manager.set_icon_manager(icon_manager)
    configure_headless_theme_application(monkeypatch, theme_manager)

    theme_manager.apply_theme("unknown-theme")

    assert theme_manager.current_theme == "light"
    assert icon_manager._icon_cache == {}


def test_apply_theme_keeps_existing_behavior_without_registered_icon_manager(
    monkeypatch: object,
) -> None:
    """要件3.2: IconManager未登録でもテーマ適用を完了できる。"""
    theme_manager = ThemeManager(cast(Tk, object()))
    configure_headless_theme_application(monkeypatch, theme_manager)

    theme_manager.apply_theme("dark")

    assert theme_manager.current_theme == "dark"


def test_apply_theme_keeps_default_treeview_row_height_for_16px_icons(
    monkeypatch: object,
) -> None:
    """16pxアイコンでは既存行レイアウトを維持するため行高を上書きしない。"""
    theme_manager = ThemeManager(cast(Tk, object()))
    configure_headless_theme_application(monkeypatch, theme_manager)

    theme_manager.apply_theme("light")

    assert HeadlessStyle.last_instance is not None
    treeview_options = next(
        options
        for style_name, options in HeadlessStyle.last_instance.configurations
        if style_name == "Treeview"
    )
    assert "rowheight" not in treeview_options


def test_apply_theme_on_macos_preserves_aqua_theme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """macOS (darwin) 環境では aqua テーマが利用可能な場合に aqua を維持する。"""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(HeadlessStyle, "_available_themes", ("aqua", "clam", "default"))
    theme_manager = ThemeManager(cast(Tk, object()))
    configure_headless_theme_application(monkeypatch, theme_manager)

    theme_manager.apply_theme("dark")

    assert HeadlessStyle.last_instance is not None
    assert HeadlessStyle.last_instance.used_themes == ["aqua"]


def test_apply_theme_to_widget_tree_styles_entry_and_panedwindow() -> None:
    """apply_theme_to_widget_tree が tk.Entry および tk.PanedWindow に期待する色を設定する。"""
    theme_manager = ThemeManager(cast(Tk, object()))
    theme = THEMES["dark"]

    mock_entry = MagicMock(spec=tk.Entry)
    mock_entry.winfo_children.return_value = []
    theme_manager.apply_theme_to_widget_tree(mock_entry, theme)

    mock_entry.config.assert_called_once_with(
        bg=theme["entry_bg"],
        fg=theme["entry_fg"],
        selectbackground=theme["select_bg"],
        selectforeground=theme["select_fg"],
        insertbackground=theme["fg"],
    )

    mock_paned = MagicMock(spec=tk.PanedWindow)
    mock_paned.winfo_children.return_value = []
    theme_manager.apply_theme_to_widget_tree(mock_paned, theme)

    mock_paned.config.assert_called_once_with(bg=theme["frame_bg"])


def test_apply_theme_on_macos_syncs_with_os_appearance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """macOS かつ Tk 8.6+ では OS のダークモード設定に連動してテーマが決定される。"""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(HeadlessStyle, "_available_themes", ("aqua", "clam", "default"))
    monkeypatch.setattr(tk, "TkVersion", 8.6)
    theme_manager = ThemeManager(cast(Tk, object()))
    configure_headless_theme_application(monkeypatch, theme_manager)

    # OS がダークモードの場合 -> アプリ設定が light でも dark に連動
    with patch("src.utils.platform_utils.is_macos_dark_mode", return_value=True):
        theme_manager.apply_theme("light")
        assert theme_manager.current_theme == "dark"

    # OS がライトモードの場合 -> light に連動
    with patch("src.utils.platform_utils.is_macos_dark_mode", return_value=False):
        theme_manager.apply_theme("dark")
        assert theme_manager.current_theme == "light"


def test_apply_theme_on_macos_tk85_forces_light_theme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """macOS かつ TkVersion < 8.6 (レガシー環境) の場合、OSがダークモードでも light テーマを強制適用する。"""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(HeadlessStyle, "_available_themes", ("aqua", "clam", "default"))
    monkeypatch.setattr(tk, "TkVersion", 8.5)
    theme_manager = ThemeManager(cast(Tk, object()))
    configure_headless_theme_application(monkeypatch, theme_manager)

    with patch("src.utils.platform_utils.is_macos_dark_mode", return_value=True):
        theme_manager.apply_theme("dark")
        assert theme_manager.current_theme == "light"
