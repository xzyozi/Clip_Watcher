"""
reusable_gui.windows.settings_window
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
スキーマ駆動の汎用設定ウィンドウ。

SettingsManager.get_settings_schema() が返す list[SettingField] を唯一の情報源とし、
タブ・グループ・ウィジェットを自動生成する。
特定アプリの設定項目はこのモジュールに一切含まれない。
"""

from __future__ import annotations

import copy
import logging
import tkinter as tk
from collections import defaultdict
from functools import partial
from tkinter import filedialog, font, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING, Any, cast

from reusable_gui.core.config import defaults as config
from reusable_gui.core.config.schema import SettingField, WidgetType

if TYPE_CHECKING:
    from reusable_gui.core.bootstrap.base_application import BaseApplication
    from reusable_gui.core.config.settings_manager import BaseSettingsManager

logger = logging.getLogger(__name__)


class SettingsWindow(tk.Toplevel):
    """スキーマ駆動の汎用設定ウィンドウ。

    SettingsManager が提供するスキーマ（list[SettingField]）を読み取り、
    タブ・グループ・ウィジェットを動的に生成する。
    アプリ固有の設定項目はスキーマとして外部から注入されるため、
    このクラス自体は完全に汎用的に保たれる。
    """

    def __init__(
        self,
        master: tk.Misc,
        app_instance: BaseApplication,
        settings_manager: BaseSettingsManager,
    ) -> None:
        super().__init__(master)
        self.app = app_instance
        if hasattr(app_instance, "theme_manager") and hasattr(
            app_instance.theme_manager, "apply_theme_to_toplevel"
        ):
            app_instance.theme_manager.apply_theme_to_toplevel(self)  # type: ignore

        self.settings_manager = settings_manager
        self.app_instance = app_instance

        self.initial_settings = copy.deepcopy(self.settings_manager.settings)
        self.settings_saved = False

        self.title(self._tr("Settings"))
        self.geometry(config.SETTINGS_WINDOW_GEOMETRY)
        self.resizable(True, True)

        # スキーマ取得
        self._schema: list[SettingField] = self._get_schema()

        # key -> tk.Variable のマップ（WidgetType に応じた型で生成）
        self._vars: dict[str, tk.Variable] = {}

        # LISTBOX_EDIT 型の値は list なので別途管理
        self._list_vars: dict[str, list[str]] = {}
        self._listbox_widgets: dict[str, tk.Listbox] = {}

        # 動的言語更新用ウィジェット追跡
        self._translatable_widgets: list[tuple[tk.Widget, str, str]] = []
        self._group_frames: list[tuple[ttk.LabelFrame, str]] = []
        self._tab_frames: dict[str, ttk.Frame] = {}

        self._init_variables()
        self._build_ui()
        self._init_language_listener()

    def _get_schema(self) -> list[SettingField]:
        """設定ウィンドウが使用するスキーマを返す。
        サブクラスでオーバーライドしてスキーマの合成や変更を行う。
        """
        return self.settings_manager.get_settings_schema()

    def _validate_pending_values(self) -> bool:
        """保存/適用前に未確定の設定値を検証するフック。
        サブクラスでオーバーライドして特定の入力検証や登録処理を行う。
        """
        return True

    # ------------------------------------------------------------------
    # 変数の初期化
    # ------------------------------------------------------------------

    def _init_variables(self) -> None:
        """スキーマを走査し、各設定項目に対応する tk.Variable を生成する。"""
        for f in self._schema:
            value: Any = self.settings_manager.get_setting(f.key, f.default)

            if f.widget_type == WidgetType.CHECKBUTTON:
                self._vars[f.key] = tk.BooleanVar(value=bool(value))

            elif f.widget_type == WidgetType.SPINBOX:
                if isinstance(value, float):
                    self._vars[f.key] = tk.DoubleVar(value=float(value))
                else:
                    self._vars[f.key] = tk.IntVar(
                        value=int(value) if value is not None else 0
                    )

            elif f.widget_type in (
                WidgetType.OPTION_MENU,
                WidgetType.FONT_PICKER,
                WidgetType.ENTRY,
                WidgetType.HOTKEY_CAPTURE,
            ):
                self._vars[f.key] = tk.StringVar(
                    value=str(value) if value is not None else ""
                )

            elif f.widget_type == WidgetType.LISTBOX_EDIT:
                # リスト型は tk.Variable では扱えないので別管理
                self._list_vars[f.key] = list(value) if value else []

    # ------------------------------------------------------------------
    # UIの構築
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Notebook・タブ・グループ・ウィジェット・ボタン群を構築する。"""
        self._build_notebook()
        self._build_action_buttons()

    def _build_notebook(self) -> None:
        """スキーマからタブ・グループ構造を推論し Notebook を構築する。"""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(
            pady=config.BUTTON_PADDING_Y,
            padx=config.BUTTON_PADDING_X,
            fill=tk.BOTH,
            expand=True,
        )

        # タブ順序を保持したまま tab -> group -> [fields] に整理
        tab_order: list[str] = []
        tab_groups: dict[str, dict[str, list[SettingField]]] = {}

        for f in self._schema:
            if f.tab not in tab_groups:
                tab_order.append(f.tab)
                tab_groups[f.tab] = defaultdict(list)
            tab_groups[f.tab][f.group].append(f)

        self._tab_frames.clear()

        for tab_name in tab_order:
            frame = ttk.Frame(self.notebook, padding=config.FRAME_PADDING)
            self.notebook.add(frame, text=self._tr(tab_name))
            self._tab_frames[tab_name] = frame
            self._render_tab(frame, tab_groups[tab_name])

    def _init_language_listener(self) -> None:
        """LANGUAGE_CHANGED イベントを購読する。"""
        self._event_dispatcher = getattr(self.app, "event_dispatcher", None) or getattr(
            self.settings_manager, "event_dispatcher", None
        )
        if self._event_dispatcher and hasattr(self._event_dispatcher, "subscribe"):
            self._event_dispatcher.subscribe(
                "LANGUAGE_CHANGED", self._on_language_changed
            )

    def _on_language_changed(self, *args: Any) -> None:
        """言語変更通知を受信した際に、全UI要素のテキストを動的に再翻訳する。"""
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        self.title(self._tr("Settings"))

        if hasattr(self, "notebook") and hasattr(self, "_tab_frames"):
            for tab_name, frame in self._tab_frames.items():
                try:
                    self.notebook.tab(frame, text=self._tr(tab_name))
                except (tk.TclError, KeyError):
                    pass

        if hasattr(self, "_group_frames"):
            for lf, group_name in self._group_frames:
                try:
                    if lf.winfo_exists():
                        lf.configure(text=self._tr(group_name))
                except (tk.TclError, KeyError):
                    pass

        if hasattr(self, "_translatable_widgets"):
            for widget, kind, raw_text in self._translatable_widgets:
                try:
                    if not widget.winfo_exists():
                        continue
                    if kind == "text":
                        cast(Any, widget).configure(text=self._tr(raw_text))
                    elif kind == "label_with_colon":
                        cast(Any, widget).configure(text=f"{self._tr(raw_text)}:")
                except (tk.TclError, KeyError):
                    pass

    def _tr(self, text: str) -> str:
        """翻訳サービスが存在する場合はテキストを翻訳し、なければそのまま返す。"""
        if hasattr(self.app, "translator") and self.app.translator:
            tr = self.app.translator
            if hasattr(tr, "get") and callable(tr.get):
                return str(tr.get(text, text))
            if hasattr(tr, "translate") and callable(tr.translate):
                return str(tr.translate(text))
            if callable(tr):
                return str(tr(text))
        return text

    def _render_tab(
        self, parent: ttk.Frame, groups: dict[str, list[SettingField]]
    ) -> None:
        """タブ内のグループ（LabelFrame）とウィジェットを描画する。"""
        for group_name, fields in groups.items():
            if group_name:
                container: tk.Widget = ttk.LabelFrame(
                    parent, text=self._tr(group_name), padding=config.FRAME_PADDING
                )
                container.pack(
                    fill=tk.X,
                    pady=config.BUTTON_PADDING_Y,
                    padx=config.BUTTON_PADDING_X,
                )
                if isinstance(container, ttk.LabelFrame):
                    self._group_frames.append((container, group_name))
            else:
                container = ttk.Frame(parent, padding=config.FRAME_PADDING)
                container.pack(fill=tk.X)

            row = 0
            for f in fields:
                row = self._render_field(container, f, row)

    def _render_field(self, parent: tk.Widget, f: SettingField, row: int) -> int:
        """WidgetType に応じてウィジェットを生成し、grid で配置する。row の次の値を返す。"""
        label_text = self._tr(f.label)
        if f.widget_type == WidgetType.CHECKBUTTON:
            cb = ttk.Checkbutton(parent, text=label_text, variable=self._vars[f.key])
            cb.grid(
                row=row,
                column=0,
                columnspan=2,
                sticky=tk.W,
                padx=config.BUTTON_PADDING_X,
                pady=config.BUTTON_PADDING_Y,
            )
            self._translatable_widgets.append((cb, "text", f.label))
            return row + 1

        elif f.widget_type == WidgetType.SPINBOX:
            lbl = ttk.Label(parent, text=f"{label_text}:")
            lbl.grid(
                row=row,
                column=0,
                sticky=tk.W,
                padx=config.BUTTON_PADDING_X,
                pady=config.BUTTON_PADDING_Y,
            )
            self._translatable_widgets.append((lbl, "label_with_colon", f.label))
            sp = ttk.Spinbox(
                parent,
                from_=f.min_value,
                to=f.max_value,
                increment=f.increment,
                textvariable=self._vars[f.key],
                width=f.width,
            )
            sp.grid(
                row=row,
                column=1,
                sticky=tk.W,
                padx=config.BUTTON_PADDING_X,
                pady=config.BUTTON_PADDING_Y,
            )
            return row + 1

        elif f.widget_type == WidgetType.OPTION_MENU:
            lbl = ttk.Label(parent, text=f"{label_text}:")
            lbl.grid(
                row=row,
                column=0,
                sticky=tk.W,
                padx=config.BUTTON_PADDING_X,
                pady=config.BUTTON_PADDING_Y,
            )
            self._translatable_widgets.append((lbl, "label_with_colon", f.label))
            var = self._vars[f.key]
            menu = ttk.OptionMenu(parent, var, var.get(), *f.choices)  # type: ignore[arg-type]
            menu.grid(
                row=row,
                column=1,
                sticky=tk.W,
                padx=config.BUTTON_PADDING_X,
                pady=config.BUTTON_PADDING_Y,
            )
            return row + 1

        elif f.widget_type == WidgetType.FONT_PICKER:
            lbl = ttk.Label(parent, text=f"{label_text}:")
            lbl.grid(
                row=row,
                column=0,
                sticky=tk.W,
                padx=config.BUTTON_PADDING_X,
                pady=config.BUTTON_PADDING_Y,
            )
            self._translatable_widgets.append((lbl, "label_with_colon", f.label))
            font_families = sorted(font.families())
            var = self._vars[f.key]
            current_val = var.get()
            # Issue #197: 存在しないフォント名が保存されている場合は安全な有効フォントにサニタイズ
            try:
                from src.utils.platform_utils import resolve_safe_font_family

                safe_val = resolve_safe_font_family(current_val, font_families)
            except Exception:
                safe_val = current_val
            if current_val != safe_val:
                var.set(safe_val)
            menu = ttk.OptionMenu(parent, var, var.get(), *font_families)  # type: ignore[arg-type]
            menu.grid(
                row=row,
                column=1,
                sticky=tk.W,
                padx=config.BUTTON_PADDING_X,
                pady=config.BUTTON_PADDING_Y,
            )
            return row + 1

        elif f.widget_type == WidgetType.ENTRY:
            lbl = ttk.Label(parent, text=f"{label_text}:")
            lbl.grid(
                row=row,
                column=0,
                sticky=tk.W,
                padx=config.BUTTON_PADDING_X,
                pady=config.BUTTON_PADDING_Y,
            )
            self._translatable_widgets.append((lbl, "label_with_colon", f.label))
            entry = ttk.Entry(parent, textvariable=self._vars[f.key], width=f.width)
            entry.grid(
                row=row,
                column=1,
                sticky=tk.EW,
                padx=config.BUTTON_PADDING_X,
                pady=config.BUTTON_PADDING_Y,
            )
            return row + 1

        elif f.widget_type == WidgetType.LISTBOX_EDIT:
            self._render_listbox_edit(parent, f)
            return (
                row + 1
            )  # LISTBOX_EDIT はグリッドではなく pack を使うため行は +1 のみ

        elif f.widget_type == WidgetType.HOTKEY_CAPTURE:
            return self._render_hotkey_capture(parent, f, row)

        logger.warning(
            "Unknown WidgetType %s for key '%s'. Skipped.", f.widget_type, f.key
        )
        return row

    def _render_hotkey_capture(
        self, parent: tk.Widget, f: SettingField, row: int
    ) -> int:
        """HOTKEY_CAPTURE 型: キー入力をキャプチャしてホットキー文字列化する Entry ウィジェット。"""
        label_text = self._tr(f.label)
        lbl = ttk.Label(parent, text=f"{label_text}:")
        lbl.grid(
            row=row,
            column=0,
            sticky=tk.W,
            padx=config.BUTTON_PADDING_X,
            pady=config.BUTTON_PADDING_Y,
        )
        self._translatable_widgets.append((lbl, "label_with_colon", f.label))

        var = self._vars[f.key]
        entry = ttk.Entry(parent, textvariable=var, width=f.width, state="readonly")
        entry.grid(
            row=row,
            column=1,
            sticky=tk.W,
            padx=config.BUTTON_PADDING_X,
            pady=config.BUTTON_PADDING_Y,
        )

        def _on_key_press(event: tk.Event) -> str | None:
            keysym = event.keysym.lower()
            if keysym in (
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
            ):
                return None

            if keysym in ("backspace", "delete"):
                var.set("")
                return "break"

            parts = []
            state = event.state if isinstance(event.state, int) else 0
            if (state & 0x0004) or "control" in keysym:
                parts.append("Ctrl")
            if (state & 0x0001) or "shift" in keysym:
                parts.append("Shift")
            if (state & 0x0020) or (state & 0x0008) or "alt" in keysym:
                parts.append("Alt")

            char = event.char
            if keysym.isalnum() and len(keysym) == 1:
                main_key = keysym.upper()
            elif char and char.isalnum() and len(char) == 1:
                main_key = char.upper()
            elif len(keysym) == 1 and keysym.isprintable():
                main_key = keysym.upper()
            else:
                return "break"

            if not parts:
                return "break"

            parts.append(main_key)
            combo_str = "+".join(parts)
            var.set(combo_str)
            return "break"

        entry.bind("<KeyPress>", _on_key_press)
        return row + 1

    def _render_listbox_edit(self, parent: tk.Widget, f: SettingField) -> None:
        """LISTBOX_EDIT 型: Listbox + Add/Remove ボタンを描画する。"""
        wrapper = ttk.Frame(parent)
        wrapper.pack(
            fill=tk.BOTH,
            expand=True,
            padx=config.BUTTON_PADDING_X,
            pady=config.BUTTON_PADDING_Y,
        )

        listbox = tk.Listbox(wrapper)
        for item in self._list_vars[f.key]:
            listbox.insert(tk.END, item)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        btn_frame = ttk.Frame(wrapper)
        btn_frame.pack(side=tk.LEFT, padx=(10, 0))

        add_btn = ttk.Button(
            btn_frame,
            text=self._tr("Add"),
            command=partial(self._add_list_item, f.key),
        )
        add_btn.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y)
        self._translatable_widgets.append((add_btn, "text", "Add"))

        remove_btn = ttk.Button(
            btn_frame,
            text=self._tr("Remove"),
            command=partial(self._remove_list_item, f.key),
        )
        remove_btn.pack(fill=tk.X, pady=config.BUTTON_PADDING_Y)
        self._translatable_widgets.append((remove_btn, "text", "Remove"))

    def _build_action_buttons(self) -> None:
        """Import / Export / Restore Defaults / Save / Cancel / Apply ボタンを構築する。"""
        # Import / Export / Restore Defaults
        io_frame = ttk.Frame(self)
        io_frame.pack(
            fill=tk.X,
            side=tk.BOTTOM,
            pady=config.BUTTON_PADDING_Y,
            padx=config.BUTTON_PADDING_X,
        )

        export_btn = ttk.Button(
            io_frame, text=self._tr("Export Settings"), command=self._export_settings
        )
        export_btn.pack(side=tk.LEFT)
        self._translatable_widgets.append((export_btn, "text", "Export Settings"))

        import_btn = ttk.Button(
            io_frame, text=self._tr("Import Settings"), command=self._import_settings
        )
        import_btn.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)
        self._translatable_widgets.append((import_btn, "text", "Import Settings"))

        restore_btn = ttk.Button(
            io_frame, text=self._tr("Restore Defaults"), command=self._restore_defaults
        )
        restore_btn.pack(side=tk.LEFT)
        self._translatable_widgets.append((restore_btn, "text", "Restore Defaults"))

        # Save / Cancel / Apply
        btn_frame = ttk.Frame(self, padding=config.FRAME_PADDING)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        save_btn = ttk.Button(
            btn_frame, text=self._tr("Save"), command=self._save_and_close
        )
        save_btn.pack(side=tk.RIGHT, padx=(10, 0))
        self._translatable_widgets.append((save_btn, "text", "Save"))

        cancel_btn = ttk.Button(
            btn_frame, text=self._tr("Cancel"), command=self.destroy
        )
        cancel_btn.pack(side=tk.RIGHT)
        self._translatable_widgets.append((cancel_btn, "text", "Cancel"))

        apply_btn = ttk.Button(
            btn_frame, text=self._tr("Apply"), command=self._apply_only
        )
        apply_btn.pack(side=tk.RIGHT)
        self._translatable_widgets.append((apply_btn, "text", "Apply"))

    # ------------------------------------------------------------------
    # リスト操作（LISTBOX_EDIT）
    # ------------------------------------------------------------------

    def _add_list_item(self, key: str) -> None:
        prompt_tmpl = self._tr("Enter value for '{key}':")
        prompt = (
            prompt_tmpl.format(key=key)
            if "{key}" in prompt_tmpl
            else f"{prompt_tmpl} {key}"
        )
        new_item: str | None = simpledialog.askstring(
            self._tr("Add Item"), prompt, parent=self
        )
        if new_item and new_item not in self._list_vars[key]:
            self._list_vars[key].append(new_item)
            self._listbox_widgets[key].insert(tk.END, new_item)

    def _remove_list_item(self, key: str) -> None:
        selected = self._listbox_widgets[key].curselection()
        for i in reversed(selected):
            self._listbox_widgets[key].delete(i)
            del self._list_vars[key][i]

    # ------------------------------------------------------------------
    # 設定の読み書き
    # ------------------------------------------------------------------

    def _collect_values(self) -> None:
        """全 tk.Variable と list_vars から値を収集し settings_manager に書き込む。"""
        for f in self._schema:
            if f.widget_type == WidgetType.LISTBOX_EDIT:
                self.settings_manager.set_setting(f.key, list(self._list_vars[f.key]))
            else:
                self.settings_manager.set_setting(f.key, self._vars[f.key].get())

    def _update_ui_from_settings(self) -> None:
        """設定値を settings_manager から再読み込みし、全 UI 変数を更新する。"""
        for f in self._schema:
            value: Any = self.settings_manager.get_setting(f.key, f.default)

            if f.widget_type == WidgetType.LISTBOX_EDIT:
                self._list_vars[f.key] = list(value) if value else []
                lb = self._listbox_widgets[f.key]
                lb.delete(0, tk.END)
                for item in self._list_vars[f.key]:
                    lb.insert(tk.END, item)
            else:
                try:
                    self._vars[f.key].set(value)
                except (tk.TclError, KeyError) as e:
                    logger.warning("Failed to update UI for key '%s': %s", f.key, e)

    # ------------------------------------------------------------------
    # アクション
    # ------------------------------------------------------------------

    def _apply_only(self) -> None:
        if not self._validate_pending_values():
            return
        self._collect_values()
        self.settings_manager.notify_listeners()

    def _save_and_close(self) -> None:
        if not self._validate_pending_values():
            return
        self._collect_values()
        self.settings_manager.save_settings()
        self.settings_saved = True
        logger.info("Settings saved.")
        self.destroy()

    def _export_settings(self) -> None:
        filepath: str | None = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[
                (self._tr("JSON files"), "*.json"),
                (self._tr("All files"), "*.*"),
            ],
            title=self._tr("Export Settings"),
        )
        if filepath:
            self.settings_manager.save_settings_to_file(filepath)
            logger.info("Settings exported to %s", filepath)
            msg_tmpl = self._tr("Settings exported to {filepath}")
            msg = (
                msg_tmpl.format(filepath=filepath)
                if "{filepath}" in msg_tmpl
                else f"{msg_tmpl}: {filepath}"
            )
            messagebox.showinfo(self._tr("Export Successful"), msg)

    def _import_settings(self) -> bool:
        filepath: str | None = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[
                (self._tr("JSON files"), "*.json"),
                (self._tr("All files"), "*.*"),
            ],
            title=self._tr("Import Settings"),
        )
        if filepath:
            if self.settings_manager.load_settings_from_file(filepath):
                self._update_ui_from_settings()
                messagebox.showinfo(
                    self._tr("Import Successful"),
                    self._tr("Settings imported successfully."),
                )
                return True
            else:
                logger.error("Could not load settings from: %s", filepath)
                messagebox.showerror(
                    self._tr("Import Failed"),
                    self._tr("Could not load settings from the selected file."),
                )
        return False

    def _restore_defaults(self) -> None:
        if messagebox.askyesno(
            self._tr("Restore Defaults"),
            self._tr(
                "Are you sure you want to restore all settings to their default values?"
            ),
        ):
            self.settings_manager.settings = (
                self.settings_manager._get_default_settings()
            )
            self._update_ui_from_settings()
            logger.info("Settings restored to defaults.")

    def destroy(self) -> None:
        if (
            hasattr(self, "_event_dispatcher")
            and self._event_dispatcher
            and hasattr(self._event_dispatcher, "unsubscribe")
        ):
            try:
                self._event_dispatcher.unsubscribe(
                    "LANGUAGE_CHANGED", self._on_language_changed
                )
            except Exception:
                pass

        if (
            not self.settings_saved
            and self.settings_manager.settings != self.initial_settings
        ):
            self.settings_manager.settings = copy.deepcopy(self.initial_settings)
            self.settings_manager.notify_listeners()
        super().destroy()
