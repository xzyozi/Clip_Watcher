from __future__ import annotations

import ctypes
import os
import sys
import tkinter as tk
import traceback
from tkinter import messagebox
from typing import TYPE_CHECKING

from src.core.bootstrap.application_builder import ApplicationBuilder
from src.utils.logging_config import setup_logging

# Import standalone handlers so they can be accessed via the package
from . import main_handlers  # noqa: F401
from .file_handlers import FileEventHandlers
from .history_handlers import HistoryEventHandlers
from .settings_handlers import SettingsEventHandlers

if TYPE_CHECKING:
    from src.core.bootstrap.base_application import BaseApplication


_MUTEX_NAME = "Local\\ClipWatcher_SingleInstance_Mutex"
_ERROR_ALREADY_EXISTS = 183


def register_class_based_handlers(app_instance: BaseApplication) -> None:
    """
    Initializes and registers all class-based event handlers for the application.
    """
    app_instance.history_handlers = HistoryEventHandlers(
        app_instance, app_instance.event_dispatcher, app_instance.undo_manager
    )  # type: ignore
    app_instance.file_handlers = FileEventHandlers(
        app_instance, app_instance.event_dispatcher
    )  # type: ignore
    app_instance.settings_handlers = SettingsEventHandlers(
        app_instance.event_dispatcher, app_instance.settings_manager
    )  # type: ignore


def _acquire_windows_mutex() -> tuple[int | None, bool]:
    """Windows の名前付きミューテックスを取得し、重複起動かを返す。"""
    if sys.platform != "win32":
        return None, False

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_mutex = kernel32.CreateMutexW
    create_mutex.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    create_mutex.restype = ctypes.c_void_p

    mutex_handle = create_mutex(None, False, _MUTEX_NAME)
    if not mutex_handle:
        raise ctypes.WinError(ctypes.get_last_error())

    if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(ctypes.c_void_p(mutex_handle))
        return None, True

    return int(mutex_handle), False


def _release_windows_mutex(mutex_handle: int | None) -> None:
    """取得済みの Windows 名前付きミューテックスのハンドルを閉じる。"""
    if sys.platform == "win32" and mutex_handle is not None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle(ctypes.c_void_p(mutex_handle))


def start_app() -> None:
    mutex_handle: int | None = None
    try:
        # --- Single Instance Check ---
        mutex_handle, already_running = _acquire_windows_mutex()
        if already_running:
            messagebox.showinfo("Already Running", "Clip Watcher is already running.")
            return

        # --- Path Definitions ---
        if sys.platform == "win32":
            app_data_dir = os.path.join(os.environ["USERPROFILE"], ".clipWatcher")
        else:
            app_data_dir = os.path.join(os.path.expanduser("~"), ".clipwatcher")
        os.makedirs(app_data_dir, exist_ok=True)

        history_file_path = os.path.join(app_data_dir, "history.json")
        settings_file_path = os.path.join(app_data_dir, "settings.json")
        db_path = os.path.join(app_data_dir, "clip_watcher.db")

        # --- Logging ---
        logger = setup_logging()
        logger.info("アプリケーションを開始します")

        # --- Migration ---
        try:
            from scripts.migrate_json_to_sqlite import main as run_migration

            run_migration()
        except Exception as e:
            logger.error(
                "マイグレーションの実行中にエラーが発生しました: %s",
                str(e),
                exc_info=True,
            )

        # --- Application Setup ---
        root = tk.Tk()

        builder = ApplicationBuilder()
        app = (
            builder.with_event_dispatcher()
            .with_dependency_check()
            .with_settings(settings_file_path)
            .with_database(db_path)
            .with_translator()
            .with_theme_manager(root)
            .with_icon_manager()
            .with_history_service()
            .with_text_workflow_service(root, app_data_dir)
            .with_plugin_manager()
            .with_window_state_manager(root)
            .with_global_hotkey_listener(root)
            .with_hotkey_registration_manager()
            .with_clipboard_monitor(root, history_file_path)
            .build(root)
        )

        logger.info("アプリケーションの初期化が完了しました")

        root.mainloop()

    except Exception as e:
        # Use a local logger variable to avoid UnboundLocalError
        local_logger = locals().get("logger")
        if local_logger:
            local_logger.error(f"アプリケーション起動エラー: {str(e)}", exc_info=True)
        else:
            print(f"アプリケーション起動エラー: {str(e)}")
        traceback.print_exc()
    finally:
        _release_windows_mutex(mutex_handle)
