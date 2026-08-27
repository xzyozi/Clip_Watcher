import tkinter as tk
from tkinter import Tk, Toplevel, ttk
from typing import Any

from src.core.config.defaults import THEMES
from src.gui.icon_manager import IconManager


class ThemeManager:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.current_theme = "light"
        self.menubar: tk.Menu | None = None
        self.icon_manager: IconManager | None = None

    def set_menubar(self, menubar: tk.Menu) -> None:
        self.menubar = menubar

    def set_icon_manager(self, icon_manager: IconManager) -> None:
        """テーマ切替時に通知するIconManagerを登録する。"""
        self.icon_manager = icon_manager

    def apply_theme(self, theme_name: str) -> None:
        # Requirements 8.3: このメソッドは途中で例外が発生した場合に、それまでに適用済みの
        # スタイル変更や self.current_theme を切替前の状態へ巻き戻す処理を持たない。
        # 下記の try/except tk.TclError（'clam'テーマ選択・選択スタイルマッピング）は、
        # 個々のワークアラウンド適用が失敗した場合の代替手段（フォールバック）であり、
        # apply_theme() 全体の適用を取り消す「ロールバック」ではない。ここで捕捉されない
        # 例外が発生した場合は、既存の例外伝播に委ね、ピン留め表示行を含む状態は
        # 失敗時点のままとする。
        if theme_name not in THEMES:
            print(f"Theme '{theme_name}' not found. Falling back to 'light'.")
            theme_name = "light"
        self.current_theme = theme_name
        theme = THEMES[theme_name]

        if self.icon_manager is not None:
            self.icon_manager.invalidate_theme(theme_name)

        # 1. Configure ttk styles
        style = ttk.Style(self.root)
        if theme_name == "dark":
            try:
                style.theme_use("clam")
            except tk.TclError:
                # Requirements 7.5: 'clam' テーマが利用できない環境では、
                # 選択スタイルのワークアラウンド（'clam'前提）を適用できないため、
                # 対応可能な 'default' テーマへ自動的にフォールバックする。
                style.theme_use("default")
                theme_name = "default"
        else:
            style.theme_use("default")

        style.configure(".", background=theme["bg"], foreground=theme["fg"])
        style.configure("TFrame", background=theme["frame_bg"])
        style.configure(
            "TLabel", background=theme["frame_bg"], foreground=theme["label_fg"]
        )
        style.configure(
            "TLabelFrame", background=theme["frame_bg"], foreground=theme["label_fg"]
        )
        style.configure(
            "TButton", background=theme["button_bg"], foreground=theme["button_fg"]
        )
        style.map("TButton", background=[("active", theme["button_bg"])])

        # Custom button styles for calendar
        style.configure(
            "Today.TButton",
            background=theme.get("highlight_bg", theme["button_bg"]),
            foreground=theme["button_fg"],
        )
        style.map(
            "Today.TButton",
            background=[("active", theme.get("highlight_bg", theme["button_bg"]))],
        )
        style.configure(
            "Selected.TButton",
            background=theme["select_bg"],
            foreground=theme["select_fg"],
        )
        style.map("Selected.TButton", background=[("active", theme["select_bg"])])

        style.configure(
            "TCheckbutton", background=theme["frame_bg"], foreground=theme["label_fg"]
        )
        style.configure(
            "TRadiobutton", background=theme["frame_bg"], foreground=theme["label_fg"]
        )
        style.configure(
            "TEntry",
            fieldbackground=theme["entry_bg"],
            foreground=theme["entry_fg"],
            insertbackground=theme["fg"],
        )
        style.configure(
            "TSpinbox", fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"]
        )
        style.configure(
            "TCombobox", fieldbackground=theme["entry_bg"], foreground=theme["entry_fg"]
        )

        # Notebook specific styling
        style.configure(
            "TNotebook", background=theme["bg"], bordercolor=theme["frame_bg"]
        )
        style.configure(
            "TNotebook.Tab", background=theme["frame_bg"], foreground=theme["label_fg"]
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", theme["bg"])],
            foreground=[("selected", theme["fg"])],
        )

        # Treeview specific styling
        style.configure(
            "Treeview",
            background=theme["listbox_bg"],
            foreground=theme["listbox_fg"],
            fieldbackground=theme["listbox_bg"],
        )
        if theme_name == "dark":
            # 既知の不具合ワークアラウンド（Requirements 7.4）:
            # 'clam' テーマでは、Treeviewの選択状態スタイルマップ（'selected'）が
            # tag_configure() で設定した行の背景色（例: ピン留め行の pinned タグ）を
            # 無条件に上書きしてしまう。選択状態の背景/前景マッピングを空にすることで、
            # 選択されていてもタグ側の背景色が視認可能な状態を維持する。
            try:
                style.map("Treeview", background=[], foreground=[])
            except tk.TclError:
                # Requirements 7.5: ワークアラウンドの適用自体が失敗した場合、
                # 選択マッピングを完全に諦めるのではなく、通常の選択色マッピング
                # にフォールバックし、視認性が完全に失われる事態を避ける。
                style.map(
                    "Treeview",
                    background=[("selected", theme["select_bg"])],
                    foreground=[("selected", theme["select_fg"])],
                )
        else:
            style.map(
                "Treeview",
                background=[("selected", theme["select_bg"])],
                foreground=[("selected", theme["select_fg"])],
            )
        style.configure(
            "Treeview.Heading",
            background=theme["button_bg"],
            foreground=theme["button_fg"],
        )

        # 2. Recursively apply theme to non-ttk widgets
        self.apply_theme_to_widget_tree(self.root, theme)

        # 3. Apply theme to menubar
        if self.menubar:
            self._apply_theme_to_menu(self.menubar, theme)

    def _apply_theme_to_menu(self, menu: tk.Menu, theme: dict[str, str]) -> None:
        try:
            menu.config(  # type: ignore
                background=theme.get("menu_bg"),
                foreground=theme.get("menu_fg"),
                activebackground=theme.get("active_menu_bg"),
                activeforeground=theme.get("active_menu_fg"),
                relief=tk.FLAT,
                borderwidth=0,
            )
        except tk.TclError:
            pass  # May fail on some systems

        try:
            end_index = menu.index("end")
            if end_index is not None:
                for i in range(end_index + 1):
                    if menu.type(i) == "cascade":
                        submenu_name = menu.entrycget(i, "menu")
                        if submenu_name:
                            submenu = menu.nametowidget(submenu_name)
                            self._apply_theme_to_menu(submenu, theme)
        except (tk.TclError, AttributeError):
            # This can fail on some systems or if the menu is torn off
            pass

    def apply_theme_to_widget_tree(
        self, widget: tk.Misc, theme: dict[str, Any]
    ) -> None:
        try:
            if isinstance(widget, (tk.Tk, tk.Toplevel, tk.Frame, tk.LabelFrame)):
                widget.config(bg=theme["bg"])
            elif isinstance(widget, (tk.Text, tk.Listbox)):
                widget.config(
                    bg=theme["listbox_bg"],
                    fg=theme["listbox_fg"],
                    selectbackground=theme["select_bg"],
                    selectforeground=theme["select_fg"],
                )
            elif isinstance(widget, tk.Button):
                widget.config(
                    bg=theme["button_bg"],
                    fg=theme["button_fg"],
                    activebackground=theme["select_bg"],
                    activeforeground=theme["select_fg"],
                )
            elif isinstance(widget, (tk.Checkbutton, tk.Radiobutton)):
                widget.config(
                    bg=theme["button_bg"],
                    fg=theme["button_fg"],
                    activebackground=theme["select_bg"],
                    activeforeground=theme["select_fg"],
                    selectcolor=theme["frame_bg"],
                )
            elif isinstance(widget, tk.Label):
                widget.config(bg=theme["bg"], fg=theme["label_fg"])

        except (tk.TclError, AttributeError):
            pass  # Ignore errors for widgets that don't support these properties

        for child in widget.winfo_children():
            self.apply_theme_to_widget_tree(child, theme)

    def apply_theme_to_toplevel(self, toplevel_window: Toplevel) -> None:
        """Applies the current theme to a Toplevel window and its children."""
        theme = THEMES[self.current_theme]
        self.apply_theme_to_widget_tree(toplevel_window, theme)

    def get_current_theme(self) -> str:
        return self.current_theme
