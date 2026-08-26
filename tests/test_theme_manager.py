from __future__ import annotations

from tkinter import Tk
from typing import cast

from src.gui.icon_manager import IconManager
from src.gui.theme_manager import ThemeManager


class HeadlessStyle:
    """Tkの表示サーバーなしでテーマ適用を検証するための最小限のStyle代替。"""

    def __init__(self, root: Tk) -> None:
        self.root = root

    def theme_use(self, theme_name: str) -> None:
        pass

    def configure(self, style_name: str, **options: str) -> None:
        pass

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
