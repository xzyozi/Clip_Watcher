from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Mapping
from tkinter import font, ttk
from typing import TYPE_CHECKING, Any

from src.core.config import defaults as config
from src.core.config.defaults import THEMES
from src.gui.base.base_frame_gui import BaseFrameGUI
from src.gui.components import HistoryListComponent

# from src.core.config.tool_config import TOOL_COMPONENTS
from src.gui.custom_widgets import CustomEntry, CustomText
from src.gui.windows.meta_management_window import MetaManagementFrame
from src.utils.platform_utils import resolve_safe_font_family

if TYPE_CHECKING:
    from src.core.bootstrap.base_application import BaseApplication
    from src.plugins.gui_plugin import GuiPlugin

logger = logging.getLogger(__name__)


class ClipWatcherGUI(BaseFrameGUI):
    def __init__(self, master: tk.Tk, app_instance: BaseApplication) -> None:
        super().__init__(master, app_instance)
        logger.info(
            "[DIAG-GUI] ClipWatcherGUI の初期化を開始します (master=%s)", master
        )
        master.geometry(config.MAIN_WINDOW_GEOMETRY)

        self.history_data: list[tuple[str, bool, float]] = []
        self.is_user_editing: bool = False  # Flag to prevent UI updates during editing
        # 編集セッションの保存先（start_editing で確定し、finish_editing で消費する）
        self.editing_item_id: float | None = None
        self.editing_original_text: str | None = None
        # テキストエリアに表示している内容の由来。編集の保存先は「現在の選択行」ではなく
        # この由来で決める（選択変更とFocusOutの処理順に依存して別項目を上書きしないため）。
        # _text_source_item_id: 履歴行由来ならその履歴ID、現在のクリップボード由来なら None
        # _text_source_text: 表示時点の内容（未編集判定の基準。不明なら None）
        self._text_source_item_id: float | None = None
        self._text_source_text: str | None = None

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(
            pady=config.BUTTON_PADDING_Y,
            padx=config.BUTTON_PADDING_X,
            fill=tk.BOTH,
            expand=True,
        )
        logger.info("[DIAG-GUI] Notebook を配置しました")

        self.clipboard_tab_frame = ttk.Frame(
            self.notebook, padding=config.FRAME_PADDING
        )
        self.notebook.add(
            self.clipboard_tab_frame, text=""
        )  # Text set in _update_widget_text

        paned_window = tk.PanedWindow(
            self.clipboard_tab_frame,
            orient=tk.VERTICAL,
            sashrelief=tk.RAISED,
            bg=THEMES[self.app.theme_manager.get_current_theme()]["frame_bg"],
        )  # type: ignore
        paned_window.pack(fill=tk.BOTH, expand=True)

        self.current_clipboard_frame = ttk.LabelFrame(
            paned_window, text=""
        )  # Text set in _update_widget_text
        paned_window.add(self.current_clipboard_frame, height=100)

        self.redo_button = ttk.Button(
            self.current_clipboard_frame,
            text="⟳",
            command=lambda: self.app.event_dispatcher.dispatch(
                "REQUEST_REDO_LAST_ACTION"
            ),
            state=tk.DISABLED,
        )  # type: ignore
        self.redo_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.undo_button = ttk.Button(
            self.current_clipboard_frame,
            text="⟲",
            command=lambda: self.app.event_dispatcher.dispatch(
                "REQUEST_UNDO_LAST_ACTION"
            ),
            state=tk.DISABLED,
        )  # type: ignore
        self.undo_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.clipboard_text_scrollbar = ttk.Scrollbar(
            self.current_clipboard_frame, orient="vertical"
        )
        self.clipboard_text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.clipboard_text_widget = CustomText(
            self.current_clipboard_frame,
            wrap=tk.WORD,
            height=5,
            relief=tk.FLAT,
            yscrollcommand=self.clipboard_text_scrollbar.set,
            translator=self.app.translator,
            language_events=self.app.event_dispatcher,
        )
        self.clipboard_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.clipboard_text_scrollbar.config(command=self.clipboard_text_widget.yview)

        self.clipboard_text_widget.config(state=tk.NORMAL)
        # Bind focus events to control editing state
        self.clipboard_text_widget.bind("<FocusIn>", self.start_editing)
        self.clipboard_text_widget.bind("<FocusOut>", self.finish_editing)

        history_area_frame = ttk.Frame(paned_window)
        paned_window.add(history_area_frame)

        self.search_frame = ttk.Frame(history_area_frame)
        self.search_frame.pack(
            fill=tk.X, pady=config.BUTTON_PADDING_Y, padx=config.BUTTON_PADDING_X
        )

        self.search_label = ttk.Label(
            self.search_frame, text=""
        )  # Text set in _update_widget_text
        self.search_label.pack(side=tk.LEFT)

        self.search_entry = CustomEntry(
            self.search_frame,
            translator=self.app.translator,
            language_events=self.app.event_dispatcher,
        )
        self.search_entry.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=config.BUTTON_PADDING_X
        )
        self.search_entry.bind(
            "<KeyRelease>",
            lambda event: self.app.event_dispatcher.dispatch(
                "HISTORY_SEARCH", self.search_entry.get()
            ),
        )  # type: ignore

        self.history_container_frame = ttk.LabelFrame(
            history_area_frame, text=""
        )  # Text set in _update_widget_text
        self.history_container_frame.pack(
            fill=tk.BOTH,
            expand=True,
            pady=config.BUTTON_PADDING_Y,
            padx=config.BUTTON_PADDING_X,
        )
        self.history_component = HistoryListComponent(
            self.history_container_frame, self.app
        )
        self.history_component.pack(fill=tk.BOTH, expand=True)

        self.control_frame = ttk.Frame(history_area_frame)
        self.control_frame.pack(pady=config.FRAME_PADDING)

        self.copy_history_button = ttk.Button(
            self.control_frame,
            text="",
            command=lambda: self.app.event_dispatcher.dispatch(
                "HISTORY_COPY_SELECTED", self.get_selected_history_ids()
            ),
        )  # type: ignore
        self.copy_history_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.sort_button = ttk.Button(
            self.control_frame,
            text="",
            command=lambda: self.app.event_dispatcher.dispatch("HISTORY_TOGGLE_SORT"),
        )  # type: ignore
        self.sort_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.format_button = ttk.Button(
            self.control_frame,
            text="",
            command=lambda: self.app.event_dispatcher.dispatch("HISTORY_FORMAT_ITEM"),
            state=tk.DISABLED,
        )  # type: ignore
        self.format_button.pack(side=tk.LEFT, padx=config.BUTTON_PADDING_X)

        self.quit_button = ttk.Button(
            self.control_frame, text="", command=self.app.file_handlers.handle_quit
        )  # type: ignore
        self.quit_button.pack(side=tk.RIGHT, padx=config.BUTTON_PADDING_X)

        self.meta_management_tab_frame = ttk.Frame(
            self.notebook, padding=config.FRAME_PADDING
        )
        self.notebook.add(
            self.meta_management_tab_frame, text=""
        )  # Text set in _update_widget_text
        self.meta_management_frame = MetaManagementFrame(
            self.meta_management_tab_frame, self.app
        )
        self.meta_management_frame.pack(fill=tk.BOTH, expand=True)

        self.plugin_tab_frames: list[tk.Frame] = []  # Keep track of created frames

        self.app.event_dispatcher.subscribe(
            "UNDO_REDO_STACK_CHANGED", self._update_undo_redo_buttons
        )  # type: ignore
        self.app.event_dispatcher.subscribe(
            "SETTINGS_CHANGED", self.on_settings_changed
        )  # type: ignore
        self.app.event_dispatcher.subscribe(
            "HISTORY_SELECTION_CHANGED", self._on_history_selection_changed
        )  # type: ignore
        self.app.event_dispatcher.subscribe(
            "LANGUAGE_CHANGED", self._update_widget_text
        )  # type: ignore

        self.on_font_settings_changed(self.app.settings_manager.settings)  # type: ignore
        self._create_plugin_tabs()
        self._update_widget_text()  # Initial text setup
        self.notebook.bind("<Button-1>", self.handle_global_click, add="+")

        if hasattr(master, "update_idletasks"):
            master.update_idletasks()

        tabs = self.notebook.tabs() if hasattr(self.notebook, "tabs") else ()
        children_count = (
            len(master.winfo_children()) if hasattr(master, "winfo_children") else 0
        )
        logger.info(
            "[DIAG-GUI] ClipWatcherGUI 初期化完了: タブ数=%d, root子ウィジェット数=%d",
            len(tabs),
            children_count,
        )

    def handle_global_click(self, event: tk.Event) -> None:
        """
        Handles a click anywhere in the notebook. If the click is outside
        the main text widget while it has focus, treat it as a focus-out
        event to ensure the content is saved. This is a workaround for
        cases where the <FocusOut> event doesn't fire as expected when
        clicking on other widgets within the same window.
        """
        focused_widget = self.focus_get()

        if (
            focused_widget == self.clipboard_text_widget
            and event.widget != self.clipboard_text_widget
        ):
            self.finish_editing(event)

    def start_editing(self, event: tk.Event | None = None) -> None:
        """User starts editing the text area. Binds the currently selected item ID and original text."""
        self.is_user_editing = True

        # テキストエリアの由来が分かる場合はそれを保存先にする。フォーカス取得の時点で
        # 選択だけが先に別行へ移っていても、表示中の内容と異なる行を保存先にしないため。
        source_text = getattr(self, "_text_source_text", None)
        if source_text is not None:
            self.editing_item_id = getattr(self, "_text_source_item_id", None)
            self.editing_original_text = source_text
            return

        selected_indices: tuple[int, ...] = (
            self.history_component.get_selected_indices()
            if hasattr(self, "history_component")
            else ()
        )
        if selected_indices:
            index: int = selected_indices[0]
            displayed_history = self.history_component.displayed_history
            if 0 <= index < len(displayed_history):
                original_text, _, item_id = displayed_history[index]
                self.editing_item_id = item_id
                self.editing_original_text = original_text
                return

        self.editing_item_id = None
        if hasattr(self, "clipboard_text_widget"):
            self.editing_original_text = self.clipboard_text_widget.get("1.0", "end-1c")
        else:
            self.editing_original_text = None

    def finish_editing(self, event: tk.Event | None = None) -> None:
        """
        Handles the end of a user's editing session in the text widget.
        If a history item was being edited, it performs an undoable in-place update.
        Otherwise, it treats the edit as a new clipboard entry if content changed.
        """
        if not self.is_user_editing:
            return

        self.is_user_editing = False
        target_item_id = getattr(self, "editing_item_id", None)
        target_original_text = getattr(self, "editing_original_text", None)
        self.editing_item_id = None
        self.editing_original_text = None

        edited_text: str = self.clipboard_text_widget.get("1.0", "end-1c")

        if not edited_text:
            return

        # start_editing() を経由していない場合は、テキストエリアの由来を保存先にする。
        # 現在の選択行は使わない（選択だけが先に別行へ移っていても上書きしないため）。
        if target_item_id is None and target_original_text is None:
            target_item_id = getattr(self, "_text_source_item_id", None)
            target_original_text = getattr(self, "_text_source_text", None)

        # Fallback for callers/tests that manually set is_user_editing without a known source
        if target_item_id is None and target_original_text is None:
            selected_indices: tuple[int, ...] = (
                self.history_component.get_selected_indices()
                if hasattr(self, "history_component")
                else ()
            )
            if selected_indices:
                index: int = selected_indices[0]
                displayed_history = self.history_component.displayed_history
                if 0 <= index < len(displayed_history):
                    target_original_text, _, target_item_id = displayed_history[index]

        if target_item_id is not None:
            if edited_text != target_original_text:
                from src.core.events.commands import UpdateHistoryCommand

                command = UpdateHistoryCommand(
                    history_service=self.app.history_service,  # type: ignore
                    item_id=target_item_id,
                    original_text=(
                        target_original_text if target_original_text is not None else ""
                    ),
                    new_text=edited_text,
                )
                self.app.undo_manager.execute_command(command)  # type: ignore
                self._text_source_text = edited_text
        else:
            if target_original_text is None or edited_text != target_original_text:
                self.app.monitor.update_clipboard(edited_text)  # type: ignore
                self._text_source_text = edited_text

    def _set_text_area(self, content: str, item_id: float | None) -> None:
        """テキストエリアを置き換え、その内容の由来（履歴ID・基準テキスト）を記録する。"""
        self.clipboard_text_widget.config(state=tk.NORMAL)
        self.clipboard_text_widget.delete(1.0, tk.END)
        self.clipboard_text_widget.insert(tk.END, content)
        self._text_source_item_id = item_id
        self._text_source_text = content

    def _update_widget_text(self) -> None:
        """Updates all translatable text widgets."""
        translator = self.app.translator  # type: ignore
        self.master.title(translator("app_title"))  # type: ignore
        self.notebook.tab(self.clipboard_tab_frame, text=translator("clipboard_tab"))
        self.current_clipboard_frame.config(
            text=translator("current_clipboard_content_label")
        )

        if not self.clipboard_text_widget.get("1.0", "end-1c"):
            history_service = getattr(self.app, "history_service", None)
            current_content = (
                history_service.last_clipboard_data if history_service else ""
            )
            if current_content:
                self.clipboard_text_widget.insert(tk.END, current_content)
                self._text_source_item_id = None
                self._text_source_text = current_content
            else:
                waiting_text = translator("waiting_for_clipboard_content")
                self.clipboard_text_widget.insert(tk.END, waiting_text)
                # 案内文は履歴由来ではないため、未編集のまま履歴へ保存されないよう基準に記録する
                self._text_source_item_id = None
                self._text_source_text = waiting_text

        self.search_label.config(text=translator("search_label"))
        self.history_container_frame.config(text=translator("clipboard_history_label"))
        self.copy_history_button.config(text=translator("copy_selected_button"))

        sort_key = (
            "sort_asc_button" if self.app.history_sort_ascending else "sort_desc_button"
        )  # type: ignore
        self.sort_button.config(text=translator(sort_key))

        self.format_button.config(text=translator("format_button"))
        self.quit_button.config(text=translator("quit_button"))
        self.notebook.tab(
            self.meta_management_tab_frame, text=translator("meta_management_tab")
        )

    def _destroy_plugin_tabs(self) -> None:
        for frame in self.plugin_tab_frames:
            self.notebook.forget(frame)
            frame.destroy()
        self.plugin_tab_frames = []

    def _create_plugin_tabs(self) -> None:
        """Dynamically creates GUI tabs from plugins based on settings."""
        self._destroy_plugin_tabs()  # Clear existing plugin tabs
        gui_plugins: list[GuiPlugin] = self.app.plugin_manager.get_gui_plugins()  # type: ignore
        for plugin in gui_plugins:
            setting_key = f"show_{plugin.name.lower().replace(' ', '_')}_tab"
            if self.app.settings_manager.get_setting(setting_key, True):  # type: ignore
                try:
                    component_frame: tk.Frame | None = plugin.create_gui_component(
                        self.notebook, self.app
                    )  # type: ignore
                    if component_frame:
                        self.plugin_tab_frames.append(
                            component_frame
                        )  # Track the frame
                        tab_text: str = self.app.translator(plugin.name)  # type: ignore
                        self.notebook.add(component_frame, text=tab_text)
                except Exception as e:
                    print(
                        f"Failed to create GUI component for plugin '{plugin.name}': {e}"
                    )

    def on_settings_changed(self, settings: dict[str, Any]) -> None:
        self.on_font_settings_changed(settings)
        self._create_plugin_tabs()  # Re-create tabs based on new settings

    def on_font_settings_changed(self, settings: dict[str, Any]) -> None:
        self.apply_font_settings(
            settings.get("clipboard_content_font_family", "TkDefaultFont"),
            settings.get("clipboard_content_font_size", 10),
            settings.get("history_font_family", "TkDefaultFont"),
            settings.get("history_font_size", 10),
        )

    def _update_undo_redo_buttons(self, data: dict[str, Any]) -> None:
        self.undo_button.config(state=tk.NORMAL if data["can_undo"] else tk.DISABLED)
        self.redo_button.config(state=tk.NORMAL if data["can_redo"] else tk.DISABLED)

    def _on_history_selection_changed(self, data: dict[str, Any]) -> None:
        # Issue #163: テキストエリアを置換する前に、編集中の内容を元の項目へ確定する。
        # 先に置換すると編集内容が失われ、FocusOut 側で別行へ誤保存される原因になる。
        if self.is_user_editing:
            self.finish_editing()

        selected_indices: tuple[int, ...] = data["selected_indices"]

        if selected_indices:
            self.format_button.config(state=tk.NORMAL)
            index: int = selected_indices[0]
            displayed_history = self.history_component.displayed_history
            if 0 <= index < len(displayed_history):
                content, _, item_id = displayed_history[index]
                self._set_text_area(content, item_id)
            else:
                self._set_text_area("", None)
        else:
            self.format_button.config(state=tk.DISABLED)
            self._set_text_area(
                self.app.history_service.last_clipboard_data,  # type: ignore
                None,
            )

    def apply_font_settings(
        self,
        clipboard_content_font_family: str,
        clipboard_content_font_size: int,
        history_font_family: str,
        history_font_size: int,
    ) -> None:
        # Issue #197: 存在しないフォント名が保存されている場合は安全な有効フォントに解決
        safe_clipboard_family = resolve_safe_font_family(clipboard_content_font_family)
        safe_history_family = resolve_safe_font_family(history_font_family)

        clipboard_font = font.Font(
            family=safe_clipboard_family, size=clipboard_content_font_size
        )
        history_font = font.Font(family=safe_history_family, size=history_font_size)
        self.clipboard_text_widget.config(font=clipboard_font)
        self.history_component.apply_font(history_font)

    def get_selected_history_ids(self) -> list[float]:
        """履歴一覧で選択中の項目の ID を返す（メニュー等の外部呼び出し用ファサード）。"""
        return self.history_component.get_ids_for_indices(
            self.history_component.get_selected_indices()
        )

    def update_clipboard_display(
        self,
        current_content: str,
        history: list[tuple[str, bool, float]],
        sort_ascending: bool = False,
    ) -> None:
        if self.is_user_editing:
            return

        if sort_ascending:
            pinned = [item for item in history if item[1]]
            unpinned = [item for item in history if not item[1]]
            pinned.reverse()
            unpinned.reverse()
            history = pinned + unpinned

        search_query: str = (
            self.search_entry.get() if hasattr(self, "search_entry") else ""
        )
        theme_name: str = self.app.theme_manager.get_current_theme()  # type: ignore
        theme = THEMES.get(theme_name, THEMES["light"])
        hotkey_bindings: Mapping[int, str] = self.app.get_pinned_hotkey_bindings()
        if search_query:
            displayed_history: list[tuple[str, bool, float]] = (
                self.app.history_service.get_filtered_history(search_query)
            )  # type: ignore
        else:
            displayed_history = history

        self.history_data = displayed_history
        self.history_component.update_history(displayed_history, theme, hotkey_bindings)

        # テキストエリアの上書き防止（差分チェックおよび選択操作状態の保護）
        selected_indices: tuple[int, ...] = (
            self.history_component.get_selected_indices()
        )

        # 挿入すべき新しい文字列を決定
        new_insert_content = ""
        new_source_item_id: float | None = None
        if selected_indices:
            index: int = selected_indices[0]
            if 0 <= index < len(displayed_history):
                new_insert_content, _, new_source_item_id = displayed_history[index]
        else:
            new_insert_content = current_content

        current_area_text = self.clipboard_text_widget.get("1.0", "end-1c")

        # ① もしユーザーがテキストエリア内の文字を「ドラッグ選択中」であれば、上書きを強制キャンセルする（コピー操作の保護）
        is_text_selected = bool(self.clipboard_text_widget.tag_ranges(tk.SEL))

        # ② テキストに差分がある、かつユーザーが選択操作中でない場合のみ上書きする
        if current_area_text != new_insert_content and not is_text_selected:
            waiting_placeholder = (
                self.app.translator("waiting_for_clipboard_content")
                if hasattr(self.app, "translator")
                else ""
            )
            if (
                not new_insert_content
                and not displayed_history
                and current_area_text == waiting_placeholder
            ):
                pass
            else:
                self._set_text_area(new_insert_content, new_source_item_id)

    def select_tool_tab(self, plugin_name: str) -> None:
        """Selects a notebook tab corresponding to the given plugin name."""
        for i, tab_id in enumerate(self.notebook.tabs()):
            tab_text = self.notebook.tab(tab_id, "text")
            translated_plugin_name: str = self.app.translator(plugin_name)  # type: ignore
            if tab_text == translated_plugin_name:
                self.notebook.select(i)
                break
