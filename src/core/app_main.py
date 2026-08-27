from __future__ import annotations

import logging
import os
import sys
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, Any, cast

from src import event_handlers
from src.core.bootstrap.base_application import ApplicationState, BaseApplication
from src.core.config.defaults import THEMES
from src.core.hotkey.global_hotkey_listener import GLOBAL_HOTKEY_ID
from src.core.hotkey.hotkey_registration_manager import normalize_pinned_hotkey_bindings
from src.gui import menu_bar
from src.gui.main_gui import ClipWatcherGUI
from src.gui.windows.settings_window import SettingsWindow
from src.utils.undo_manager import UndoManager

if TYPE_CHECKING:
    from src.core.clipboard.clipboard_monitor import ClipboardMonitor
    from src.core.config.settings_manager import SettingsManager
    from src.core.events.event_dispatcher import EventDispatcher
    from src.core.hotkey.hotkey_registration_manager import HotkeyRegistrationManager
    from src.db.database_manager import DatabaseManager
    from src.gui.icon_manager import IconManager
    from src.gui.theme_manager import ThemeManager
    from src.plugins.manager import PluginManager
    from src.services.history_service import HistoryService
    from src.utils.i18n import Translator

logger = logging.getLogger(__name__)


class MainApplication(BaseApplication):
    def __init__(
        self,
        master: tk.Tk,
        settings_manager: SettingsManager,
        db_manager: DatabaseManager,
        history_service: HistoryService,
        monitor: ClipboardMonitor,
        plugin_manager: PluginManager,
        event_dispatcher: EventDispatcher,
        theme_manager: ThemeManager,
        translator: Translator,
        app_status: Any,
        icon_manager: IconManager | None = None,
        window_state_manager: Any | None = None,
        hotkey_registration_manager: HotkeyRegistrationManager | None = None,
    ) -> None:
        super().__init__()
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.settings_manager = settings_manager
        self.db_manager = db_manager
        self.history_service = history_service
        self.monitor = monitor
        self.plugin_manager = plugin_manager
        self.event_dispatcher = event_dispatcher
        self.theme_manager = theme_manager
        self.icon_manager = icon_manager
        self.translator = translator
        self.app_status = app_status
        self.window_state_manager = window_state_manager
        self.hotkey_registration_manager = hotkey_registration_manager

        self.undo_manager = UndoManager(event_dispatcher)
        self.history_sort_ascending: bool = False
        self.menubar: tk.Menu | None = None

        event_handlers.register_class_based_handlers(self)  # type: ignore
        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)
        self.gui = ClipWatcherGUI(master, self)

        self.event_dispatcher.subscribe(
            "HISTORY_UPDATED", self._on_history_updated_event
        )
        self.monitor.set_error_callback(self.show_error_message)
        self._rebuild_menu(event=None)

        self.event_dispatcher.subscribe(
            "HISTORY_TOGGLE_SORT", self.on_toggle_history_sort
        )  # type: ignore
        self.event_dispatcher.subscribe("LANGUAGE_CHANGED", self._rebuild_menu)  # type: ignore
        self.event_dispatcher.subscribe(
            "GLOBAL_HOTKEY_TRIGGERED", self._on_hotkey_triggered
        )
        self.master.bind("<FocusIn>", self.on_focus_in)

    def on_ready(self) -> None:
        """Called when the application is fully initialized and ready to run."""
        self._set_state(ApplicationState.READY)
        self.update_gui(self.monitor.last_clipboard_data, self.monitor.get_history())

        if not self._reconfigure_hotkeys_from_settings():
            combo = self.settings_manager.get_setting(
                "global_hotkey_combo", "Ctrl+Shift+F"
            )
            logger.warning("起動時のホットキー登録に失敗しました: %s", combo)
            self.show_error_message(
                "Hotkey Registration Warning",
                f"Could not register global hotkey: {combo!r}. The key combination may be in use by another application.",
            )

        self.monitor.start()
        self._set_state(ApplicationState.RUNNING)

    def get_pinned_hotkey_combo(self, history_id: int) -> str | None:
        bindings = self.get_pinned_hotkey_bindings()
        return bindings.get(history_id)

    def get_pinned_hotkey_bindings(self) -> dict[int, str]:
        """現在ピン留めされている履歴のホットキー割当を返す。"""
        return self._pinned_hotkey_bindings_from_settings()

    def open_pinned_hotkey_dialog(self, history_id: int) -> None:
        from src.gui.dialogs.pinned_hotkey_dialog import PinnedHotkeyDialog

        PinnedHotkeyDialog(
            self.master,
            self.get_pinned_hotkey_combo(history_id),
            lambda combo: self.configure_pinned_hotkey(history_id, combo),
        )

    def _refresh_history_display(self) -> None:
        """現在の履歴を保持したまま一覧表示を更新する。"""
        self.update_gui(self.monitor.last_clipboard_data, self.monitor.get_history())

    def configure_pinned_hotkey(self, history_id: int, combo: str) -> bool:
        if not self._is_history_item_pinned(history_id):
            self.show_error_message(
                "Hotkey Assignment", "Only pinned history items can have a hotkey."
            )
            return False

        bindings = self._pinned_hotkey_bindings_from_settings()
        bindings[history_id] = combo
        if not self._apply_pinned_hotkey_bindings(bindings):
            self.show_error_message(
                "Hotkey Assignment",
                "Could not register the hotkey. It may be invalid or already in use.",
            )
            return False
        self._save_pinned_hotkey_bindings(bindings)
        self._refresh_history_display()
        return True

    def remove_pinned_hotkey_binding(self, history_id: int) -> bool:
        bindings = self._pinned_hotkey_bindings_from_settings()
        if history_id not in bindings:
            return True
        del bindings[history_id]
        if not self._apply_pinned_hotkey_bindings(bindings):
            logger.error("履歴ID %s のホットキー解除に失敗しました。", history_id)
            return False
        self._save_pinned_hotkey_bindings(bindings)
        self._refresh_history_display()
        return True

    def clear_pinned_hotkey_bindings(self) -> bool:
        if not self._apply_pinned_hotkey_bindings({}):
            logger.error("ピン留めホットキーの一括解除に失敗しました。")
            return False
        self._save_pinned_hotkey_bindings({})
        self._refresh_history_display()
        return True

    def _on_hotkey_triggered(self, hotkey_id: int = GLOBAL_HOTKEY_ID) -> None:
        if hotkey_id == GLOBAL_HOTKEY_ID:
            if self.window_state_manager:
                self.window_state_manager.toggle()
            return
        if not self.hotkey_registration_manager:
            return

        history_id = self.hotkey_registration_manager.history_id_for_hotkey(hotkey_id)
        if history_id is None:
            return
        for content, is_pinned, item_id in self.monitor.get_history():
            if int(item_id) == history_id and is_pinned:
                self.master.clipboard_clear()
                self.master.clipboard_append(content)
                self.monitor.notification_manager.play_notification_sound()
                self.master.after(75, self._paste_into_active_window)
                logger.info(
                    "ピン留め履歴をホットキーでクリップボードへ設定し、自動貼り付けを予約しました: ID=%s",
                    history_id,
                )
                return

        logger.warning(
            "ホットキーに紐付くピン留め履歴が見つからないため、登録を解除します: ID=%s",
            history_id,
        )
        self.remove_pinned_hotkey_binding(history_id)

    def _paste_into_active_window(self) -> None:
        from src.core.hotkey.paste_sender import WindowsPasteSender

        if not WindowsPasteSender().paste_active_window():
            logger.warning(
                "自動貼り付けに失敗しました。クリップボードには内容が設定されています。"
            )

    def _pinned_hotkey_bindings_from_settings(self) -> dict[int, str]:
        raw_bindings = self.settings_manager.get_setting("pinned_hotkey_bindings", {})
        normalized = normalize_pinned_hotkey_bindings(raw_bindings)
        return {
            history_id: combo
            for history_id, combo in normalized.items()
            if self._is_history_item_pinned(history_id)
        }

    def _is_history_item_pinned(self, history_id: int) -> bool:
        return any(
            int(item_id) == history_id and is_pinned
            for _, is_pinned, item_id in self.monitor.get_history()
        )

    def _apply_pinned_hotkey_bindings(self, bindings: dict[int, str]) -> bool:
        if not self.hotkey_registration_manager:
            return False
        enabled = self.settings_manager.get_setting("global_hotkey_enabled", True)
        combo = self.settings_manager.get_setting("global_hotkey_combo", "Ctrl+Shift+F")
        if not bindings:
            return self.hotkey_registration_manager.reconfigure(enabled, combo)
        return self.hotkey_registration_manager.reconfigure_all(
            enabled, combo, bindings
        )

    def _reconfigure_hotkeys_from_settings(self) -> bool:
        return self._apply_pinned_hotkey_bindings(
            self._pinned_hotkey_bindings_from_settings()
        )

    def _save_pinned_hotkey_bindings(self, bindings: dict[int, str]) -> None:
        serialized = {str(history_id): combo for history_id, combo in bindings.items()}
        self.settings_manager.set_setting("pinned_hotkey_bindings", serialized)
        self.settings_manager.save_settings()

    def shutdown(self) -> None:
        """Performs a clean shutdown of the application."""
        if self.hotkey_registration_manager:
            self.hotkey_registration_manager.stop()
        self.stop_monitor()
        self.monitor.save_history_to_file()

    def on_closing(self) -> None:
        """Handles the main window closing event."""
        self._set_state(ApplicationState.SHUTTING_DOWN)
        self.shutdown()
        self._set_state(ApplicationState.CLOSED)
        self.master.destroy()

    def _rebuild_menu(self, event: Any = None) -> None:
        """Destroys and recreates the main menu bar, usually for language changes."""
        if hasattr(self, "menubar") and self.menubar:  # type: ignore
            self.menubar.destroy()  # type: ignore
        self.menubar = menu_bar.create_menu_bar(self.master, self)  # type: ignore
        self.master.config(menu=self.menubar)
        self.theme_manager.set_menubar(self.menubar)  # type: ignore

    def update_gui(
        self, current_content: str, history: list[tuple[str, bool, float]]
    ) -> None:
        """Wrapper to pass sort order to the GUI."""
        self.gui.update_clipboard_display(
            current_content, history, self.history_sort_ascending
        )

    def _on_history_updated_event(self, data: dict[str, Any]) -> None:
        """履歴更新イベント（HISTORY_UPDATED）受信時のハンドラー。"""
        last_content = data.get("last_content", "")
        history = data.get("history", [])
        self.update_gui(last_content, history)

    def on_focus_in(self, event: tk.Event | None = None) -> None:
        self.reassert_topmost()

    def reassert_topmost(self) -> None:
        if self.settings_manager.get_setting("always_on_top", False):
            self.master.attributes("-topmost", False)
            self.master.attributes("-topmost", True)

    def on_settings_changed(self, settings: dict[str, Any]) -> None:
        theme: str = settings.get("theme", "light")
        if theme not in THEMES:
            theme = "light"
        self.theme_manager.apply_theme(theme)
        self.gui.history_component.apply_theme(THEMES[theme])
        if hasattr(self, "theme_var"):  # type: ignore
            self.theme_var.set(theme)  # type: ignore

        always_on_top: bool = settings.get("always_on_top", False)
        self.master.attributes("-topmost", always_on_top)
        if hasattr(self, "always_on_top_var"):  # type: ignore
            self.always_on_top_var.set(always_on_top)  # type: ignore

        startup_enabled: bool = settings.get("startup_on_boot", False)
        self._manage_startup(startup_enabled)

    def _manage_startup(self, startup_enabled: bool) -> None:
        """
        Manages the startup .bat file.
        Searches for the correct activate.bat related to the current python environment
        or standard venv folders to ensure successful activation.
        """
        if sys.platform == "win32":
            startup_folder: str = os.path.join(
                os.environ["APPDATA"],
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs",
                "Startup",
            )
            startup_script_path: str = os.path.join(startup_folder, "ClipWatcher.bat")

            try:
                if startup_enabled:
                    # 1. プロジェクトルート(main.pyがある場所)を算出
                    current_dir: str = os.path.dirname(os.path.abspath(__file__))
                    # src/core -> src -> root
                    project_root: str = os.path.abspath(
                        os.path.join(current_dir, "..", "..")
                    )
                    main_script_path: str = os.path.join(
                        project_root, "clip_watcher.py"
                    )

                    # 2. activate.bat の場所を探索する
                    # 優先度1: 現在実行中のPython (sys.executable) と同じ階層にある Scripts/activate.bat
                    # (venv環境で実行していればこれが最も確実)
                    current_python_dir: str = os.path.dirname(sys.executable)
                    activate_candidates: list[str] = [
                        os.path.join(
                            current_python_dir, "activate.bat"
                        ),  # Scriptsフォルダの中にいる場合
                        os.path.join(
                            current_python_dir, "Scripts", "activate.bat"
                        ),  # python.exeの親がルートの場合
                        os.path.join(
                            project_root, "venv", "Scripts", "activate.bat"
                        ),  # 一般的な名前 venv
                        os.path.join(
                            project_root, ".venv", "Scripts", "activate.bat"
                        ),  # 一般的な名前 .venv
                        os.path.join(
                            project_root, "env", "Scripts", "activate.bat"
                        ),  # 一般的な名前 env
                    ]

                    final_activate_path: str | None = None
                    for path in activate_candidates:
                        if os.path.exists(path):
                            final_activate_path = path
                            break

                    # 3. バッチファイルの内容を作成
                    script_content: str = "@echo off\n"
                    script_content += f'cd "{project_root}"\n'

                    if final_activate_path:
                        # バッチファイル内でファイルの存在確認をしてからcallする（安全策）
                        script_content += f'if exist "{final_activate_path}" call "{final_activate_path}"\n'
                    else:
                        # 見つからない場合はログを残すなどの対策（今回はwarningを表示）
                        print("Warning: Could not automatically find activate.bat")

                    # アクティベート後はPATHが通っているはずなので python で起動
                    # 万が一失敗したときのために start コマンドを使用
                    script_content += f'start "" python "{main_script_path}"'

                    with open(startup_script_path, "w") as f:
                        f.write(script_content)
                else:
                    if os.path.exists(startup_script_path):
                        os.remove(startup_script_path)
            except Exception as e:
                self.show_error_message(
                    "Startup Error", f"Failed to manage startup script: {e}"
                )

    def on_toggle_history_sort(self, event: Any = None) -> None:
        """Toggles the history sort order and refreshes the GUI."""
        self.history_sort_ascending = not self.history_sort_ascending

        if self.history_sort_ascending:
            self.gui.sort_button.config(text=self.translator("sort_asc_button"))  # type: ignore
        else:
            self.gui.sort_button.config(text=self.translator("sort_desc_button"))  # type: ignore

        self.update_gui(self.monitor.last_clipboard_data, self.monitor.get_history())  # type: ignore
        print(
            f"History sort order set to {'ascending' if self.history_sort_ascending else 'descending'}"
        )

    def open_settings_window(self) -> None:
        self.create_toplevel(SettingsWindow, self.settings_manager)

    def create_toplevel(
        self, toplevel_class: type[tk.Toplevel], *args: Any, **kwargs: Any
    ) -> tk.Toplevel:
        toplevel_window = cast(
            tk.Toplevel,
            cast(Any, toplevel_class)(self.master, self, *args, **kwargs),
        )

        # ToplevelClass might have a wait_window(), so the window could be destroyed
        # by the time we get here. Check if it still exists.
        if toplevel_window.winfo_exists():
            if self.settings_manager.get_setting("always_on_top", False):
                toplevel_window.attributes("-topmost", True)
            toplevel_window.transient(self.master)  # type: ignore

        return toplevel_window

    def show_error_message(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def stop_monitor(self) -> None:
        self.monitor.stop()  # type: ignore
