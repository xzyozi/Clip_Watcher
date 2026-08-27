from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class PinnedHotkeyDialog(tk.Toplevel):
    """ピン留め履歴項目に割り当てるホットキーをキャプチャするダイアログ。"""

    def __init__(
        self,
        master: tk.Misc,
        initial_combo: str | None,
        on_save: Callable[[str], bool],
    ) -> None:
        super().__init__(master)
        self._on_save = on_save
        self._combo = tk.StringVar(value=initial_combo or "")

        self.title("Assign Hotkey")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Press a modifier and an alphanumeric key:").pack(
            anchor=tk.W
        )
        entry = ttk.Entry(frame, textvariable=self._combo, width=28, state="readonly")
        entry.pack(fill=tk.X, pady=(6, 12))
        entry.bind("<KeyPress>", self._on_key_press)
        entry.focus_set()

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Save", command=self._save).pack(
            side=tk.RIGHT, padx=(0, 6)
        )

    def _on_key_press(self, event: tk.Event) -> str | None:
        keysym = event.keysym.lower()
        if keysym in {
            "control_l",
            "control_r",
            "shift_l",
            "shift_r",
            "alt_l",
            "alt_r",
            "super_l",
            "super_r",
            "win_l",
            "win_r",
        }:
            return None
        if keysym in {"backspace", "delete"}:
            self._combo.set("")
            return "break"

        state = event.state if isinstance(event.state, int) else 0
        parts: list[str] = []
        if (state & 0x0004) or "control" in keysym:
            parts.append("Ctrl")
        if (state & 0x0001) or "shift" in keysym:
            parts.append("Shift")
        if (state & 0x0020) or (state & 0x0008) or "alt" in keysym:
            parts.append("Alt")
        if not parts:
            return "break"

        if keysym.isalnum() and len(keysym) == 1:
            main_key = keysym.upper()
        elif event.char and event.char.isalnum() and len(event.char) == 1:
            main_key = event.char.upper()
        else:
            return "break"
        self._combo.set("+".join([*parts, main_key]))
        return "break"

    def _save(self) -> None:
        if self._on_save(self._combo.get()):
            self.destroy()
