from .history_handlers import HistoryEventHandlers
from .file_handlers import FileEventHandlers
from .settings_handlers import SettingsEventHandlers

# Import standalone handlers so they can be accessed via the package
from . import main_handlers

def register_class_based_handlers(app_instance):
    """
    Initializes and registers all class-based event handlers for the application.
    """
    app_instance.history_handlers = HistoryEventHandlers(app_instance, app_instance.event_dispatcher, app_instance.undo_manager)
    app_instance.file_handlers = FileEventHandlers(app_instance, app_instance.event_dispatcher)
    app_instance.settings_handlers = SettingsEventHandlers(app_instance.event_dispatcher, app_instance.settings_manager)

# --- Application Entry Point ---
import tkinter as tk
from tkinter import messagebox
import os
import sys
import socket
import traceback

from src.utils.logging_config import setup_logging
from src.core.application_builder import ApplicationBuilder

def start_app():
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
            APP_DATA_DIR = os.path.join(os.environ['USERPROFILE'], '.clipWatcher')
        else:
            APP_DATA_DIR = os.path.join(os.path.expanduser('~'), '.clipwatcher')
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        
        HISTORY_FILE_PATH = os.path.join(APP_DATA_DIR, 'history.json')
        SETTINGS_FILE_PATH = os.path.join(APP_DATA_DIR, 'settings.json')
        FIXED_PHRASES_FILE_PATH = os.path.join(APP_DATA_DIR, 'fixed_phrases.json')

        # --- Logging ---
        logger = setup_logging()
        logger.info("アプリケーションを開始します")

        # --- Application Setup ---
        root = tk.Tk()
        
        builder = ApplicationBuilder()
        app = builder.with_event_dispatcher() \
            .with_dependency_check() \
            .with_settings(SETTINGS_FILE_PATH) \
            .with_translator() \
            .with_theme_manager(root) \
            .with_fixed_phrases_manager(FIXED_PHRASES_FILE_PATH) \
            .with_plugin_manager() \
            .with_clipboard_monitor(root, HISTORY_FILE_PATH) \
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