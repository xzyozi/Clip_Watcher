import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sys
import traceback
import socket

# Define history file path
if sys.platform == "win32":
    APP_DATA_DIR = os.path.join(os.environ['APPDATA'], 'ClipWatcher')
else:
    APP_DATA_DIR = os.path.join(os.path.expanduser('~'), '.clipwatcher')

os.makedirs(APP_DATA_DIR, exist_ok=True)
HISTORY_FILE_PATH = os.path.join(APP_DATA_DIR, 'history.json')

if __name__ == "__main__":
    try:
        # --- Single Instance Check (Standard Library Method) ---
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Bind to a specific port. If this fails, another instance is running.
            lock_socket.bind(("127.0.0.1", 61957))
        except OSError:
            # Address already in use, so another instance is running.
            messagebox.showinfo("Already Running", "Clip Watcher is already running.")
            sys.exit(0)
        # --- End Single Instance Check ---

        from src.utils.logging_config import setup_logging
        from src.core.application_builder import ApplicationBuilder

        logger = setup_logging()
        
        logger.info("アプリケーションを開始します")
        
        # Get the absolute path of the directory where the script is located
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        SETTINGS_FILE_PATH = os.path.join(BASE_DIR, 'settings.json')
        FIXED_PHRASES_FILE_PATH = os.path.join(BASE_DIR, 'fixed_phrases.json')
        
        root = tk.Tk()
    
        builder = ApplicationBuilder()
        app = builder.with_event_dispatcher()\
                     .with_settings(SETTINGS_FILE_PATH)\
                     .with_theme_manager(root)\
                     .with_fixed_phrases_manager(FIXED_PHRASES_FILE_PATH)\
                     .with_plugin_manager()\
                     .with_tool_manager()\
                     .with_clipboard_monitor(root, HISTORY_FILE_PATH)\
                     .build(root)
               
        logger.info("アプリケーションの初期化が完了しました")
        
        root.mainloop()
    except Exception as e:
        if 'logger' in locals():
            logger.error(f"アプリケーション起動エラー: {str(e)}", exc_info=True)
        else:
            print(f"アプリケーション起動エラー: {str(e)}")
        traceback.print_exc()
    finally:
        if lock_socket:
            lock_socket.close()
