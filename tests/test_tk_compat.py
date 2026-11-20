"""Tk 9.0 + Python < 3.13 互換性パッチ（src/utils/tk_compat.py）の単体テスト。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.utils.tk_compat import (
    _compat_combobox_current,
    _compat_menu_index,
    apply_tk9_compat_patches,
)


def test_compat_menu_index_handles_empty_and_none_values() -> None:
    fake_menu = SimpleNamespace(
        _w=".!menu",
        tk=SimpleNamespace(call=MagicMock(return_value=""), getint=int),
    )
    assert _compat_menu_index(fake_menu, "end") is None  # type: ignore[arg-type]

    fake_menu.tk.call.return_value = "none"
    assert _compat_menu_index(fake_menu, "end") is None  # type: ignore[arg-type]

    fake_menu.tk.call.return_value = "2"
    assert _compat_menu_index(fake_menu, "end") == 2  # type: ignore[arg-type]


def test_compat_combobox_current_handles_empty_setter_and_valid_index() -> None:
    fake_combo = SimpleNamespace(
        _w=".!combobox",
        tk=SimpleNamespace(call=MagicMock(return_value=""), getint=int),
    )
    assert _compat_combobox_current(fake_combo) == -1  # type: ignore[arg-type]

    fake_combo.tk.call.return_value = None
    assert _compat_combobox_current(fake_combo) == -1  # type: ignore[arg-type]

    fake_combo.tk.call.return_value = "1"
    assert _compat_combobox_current(fake_combo) == 1  # type: ignore[arg-type]

    fake_combo.tk.call.return_value = ""
    _compat_combobox_current(fake_combo, 0)  # type: ignore[arg-type]
    fake_combo.tk.call.assert_called_with(".!combobox", "current", 0)


def test_apply_tk9_compat_patches_works_on_real_tk_widgets(tk_root: tk.Tk) -> None:
    apply_tk9_compat_patches()

    menu = tk.Menu(tk_root, tearoff=0)
    try:
        assert menu.index("end") is None
        menu.add_command(label="Item")
        assert menu.index("end") == 0
    finally:
        menu.destroy()

    combo = ttk.Combobox(tk_root, state="readonly")
    try:
        combo["values"] = ["A", "B"]
        assert combo.current() == -1
        combo.current(1)
        assert combo.current() == 1
    finally:
        combo.destroy()


def test_apply_tk9_compat_patches_swallows_assignment_errors() -> None:
    with patch("src.utils.tk_compat.tk") as mock_tk:
        type(mock_tk).Menu = property(
            lambda _: (_ for _ in ()).throw(RuntimeError("immutable"))
        )
        apply_tk9_compat_patches()  # 例外を外へ漏らさない
