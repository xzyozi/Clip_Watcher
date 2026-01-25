from __future__ import annotations

import os
import socket
import sys
import tkinter as tk
import traceback
from tkinter import messagebox
from typing import TYPE_CHECKING

from src.core.application_builder import ApplicationBuilder
from src.utils.logging_config import setup_logging

# Import standalone handlers so they can be accessed via the package
from . import main_handlers  # noqa: F401
from .file_handlers import FileEventHandlers
from .history_handlers import HistoryEventHandlers
from .settings_handlers import SettingsEventHandlers

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication


def register_class_based_handlers(app_instance: BaseApplication) -> None:
    """
    Initializes and registers all class-based event handlers for the application.
    """
    app_instance.history_handlers = HistoryEventHandlers(app_instance, app_instance.event_dispatcher, app_instance.undo_manager) # type: ignore
    app_instance.file_handlers = FileEventHandlers(app_instance, app_instance.event_dispatcher) # type: ignore
    app_instance.settings_handlers = SettingsEventHandlers(app_instance.event_dispatcher, app_instance.settings_manager) # type: ignore


def start_app() -> None:
    lock_socket = None
    try:
        # --- Single Instance Check ---
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            lock_socket.bind(("127.0.0.1", 61957))
        except OSError:
            messagebox.showinfo("Already Running", "Clip Watcher is already running.")
            sys.exit(0)

        # --- Path Definitions ---
        if sys.platform == "win32":
            app_data_dir = os.path.join(os.environ['USERPROFILE'], '.clipWatcher')
        else:
            app_data_dir = os.path.join(os.path.expanduser('~'), '.clipwatcher')
        os.makedirs(app_data_dir, exist_ok=True)

        history_file_path = os.path.join(app_data_dir, 'history.json')
        settings_file_path = os.path.join(app_data_dir, 'settings.json')
        fixed_phrases_file_path = os.path.join(app_data_dir, 'fixed_phrases.json')

        # --- Logging ---
        logger = setup_logging()
        logger.info("アプリケーションを開始します")

        # --- Application Setup ---
        root = tk.Tk()

        builder = ApplicationBuilder()
        app = builder.with_event_dispatcher() \
            .with_dependency_check() \
            .with_settings(settings_file_path) \
            .with_translator() \
            .with_theme_manager(root) \
            .with_fixed_phrases_manager(fixed_phrases_file_path) \
            .with_plugin_manager() \
            .with_clipboard_monitor(root, history_file_path) \
            .build(root)

        logger.info("アプリケーションの初期化が完了しました")

        root.mainloop()

    except Exception as e:
        # Use a local logger variable to avoid UnboundLocalError
        local_logger = locals().get('logger')
        if local_logger:
            local_logger.error(f"アプリケーション起動エラー: {str(e)}", exc_info=True)
        else:
            print(f"アプリケーション起動エラー: {str(e)}")
        traceback.print_exc()
    finally:
        if lock_socket:
            lock_socket.close()
