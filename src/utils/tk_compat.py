"""Tk 9.0 + Python < 3.13 互換性パッチユーティリティ。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any


def _compat_menu_index(self: tk.Menu, index: Any) -> int | None:
    """空メニュー index で Tk 9.0 が空文字を返し TclError になる問題を回避する。"""
    w = getattr(self, "_w", "")
    i = self.tk.call(w, "index", index)
    if i in ("none", ""):
        return None
    return self.tk.getint(i)


def _compat_combobox_current(self: ttk.Combobox, newindex: int | None = None) -> Any:
    """未選択の ttk.Combobox で Tk 9.0 が空文字を返し TclError になる問題を回避する。"""
    w = getattr(self, "_w", "")
    if newindex is not None:
        return self.tk.call(w, "current", newindex)
    raw = self.tk.call(w, "current")
    if raw in ("", None):
        return -1
    return self.tk.getint(raw)


def apply_tk9_compat_patches() -> None:
    """Tk 9.0 + Python < 3.13 で空文字列が getint に渡り TclError になるメソッドを補強する。"""
    try:
        tk.Menu.index = _compat_menu_index  # type: ignore[assignment]
        ttk.Combobox.current = _compat_combobox_current  # type: ignore[method-assign]
    except Exception:
        pass
