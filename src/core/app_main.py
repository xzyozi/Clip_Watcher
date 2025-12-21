import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sys
import socket
import traceback
from src.gui.main_gui import ClipWatcherGUI
from src.core.base_application import BaseApplication, ApplicationState
from src.gui import menu_bar
from src.gui.windows.settings_window import SettingsWindow
from src.event_handlers.history_handlers import HistoryEventHandlers
from src.event_handlers.file_handlers import FileEventHandlers
from src.event_handlers.settings_handlers import SettingsEventHandlers
from src.utils.undo_manager import UndoManager
from src.utils.logging_config import setup_logging
from src.core.application_builder import ApplicationBuilder


class MainApplication(BaseApplication):
    def __init__(self, master, settings_manager, monitor, fixed_phrases_manager, plugin_manager, event_dispatcher, theme_manager, translator, app_status):
        super().__init__()
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.settings_manager = settings_manager
        self.monitor = monitor
        self.fixed_phrases_manager = fixed_phrases_manager
        self.plugin_manager = plugin_manager
        self.event_dispatcher = event_dispatcher
        self.theme_manager = theme_manager
        self.translator = translator
        self.app_status = app_status
        self.undo_manager = UndoManager(event_dispatcher)
        self.history_sort_ascending = False

        self.history_handlers = HistoryEventHandlers(self, event_dispatcher, self.undo_manager)
        self.file_handlers = FileEventHandlers(self, event_dispatcher)
        self.settings_handlers = SettingsEventHandlers(event_dispatcher, self.settings_manager)
        
        self.gui = ClipWatcherGUI(master, self)

        self.monitor.set_gui_update_callback(self.update_gui)
        self.monitor.set_error_callback(self.show_error_message)

        self._rebuild_menu()

        self.event_dispatcher.subscribe("HISTORY_TOGGLE_SORT", self.on_toggle_history_sort)
        self.event_dispatcher.subscribe("SETTINGS_CHANGED", self.on_settings_changed)
        self.event_dispatcher.subscribe("LANGUAGE_CHANGED", self._rebuild_menu)
        
        self.master.bind("<FocusIn>", self.on_focus_in)

    def on_ready(self):
        """Called when the application is fully initialized and ready to run."""
        self._set_state(ApplicationState.READY)
        self.monitor.start()
        self._set_state(ApplicationState.RUNNING)

    def shutdown(self):
        """Performs a clean shutdown of the application."""
        self.stop_monitor()
        self.monitor.save_history_to_file()

    def on_closing(self):
        """Handles the main window closing event."""
        self._set_state(ApplicationState.SHUTTING_DOWN)
        self.shutdown()
        self._set_state(ApplicationState.CLOSED)
        self.master.destroy()

    def _rebuild_menu(self):
        """Destroys and recreates the main menu bar, usually for language changes."""
        if hasattr(self, 'menubar') and self.menubar:
            self.menubar.destroy()
        self.menubar = menu_bar.create_menu_bar(self.master, self)
        self.master.config(menu=self.menubar)
        self.theme_manager.set_menubar(self.menubar)

    def update_gui(self, current_content, history):
        """Wrapper to pass sort order to the GUI."""
        self.gui.update_clipboard_display(current_content, history, self.history_sort_ascending)

    def on_focus_in(self, event=None):
        self.reassert_topmost()

    def reassert_topmost(self):
        if self.settings_manager.get_setting("always_on_top", False):
            self.master.attributes("-topmost", False)
            self.master.attributes("-topmost", True)

    def on_settings_changed(self, settings):
        theme = settings.get("theme", "light")
        self.theme_manager.apply_theme(theme)
        if hasattr(self, 'theme_var'):
            self.theme_var.set(theme)
        
        always_on_top = settings.get("always_on_top", False)
        self.master.attributes("-topmost", always_on_top)
        if hasattr(self, 'always_on_top_var'):
            self.always_on_top_var.set(always_on_top)

        startup_enabled = settings.get("startup_on_boot", False)
        self._manage_startup(startup_enabled)

    def _manage_startup(self, startup_enabled):
        """
        Manages the startup .bat file.
        Searches for the correct activate.bat related to the current python environment
        or standard venv folders to ensure successful activation.
        """
        if sys.platform == "win32":
            startup_folder = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            startup_script_path = os.path.join(startup_folder, "ClipWatcher.bat")

            try:
                if startup_enabled:
                    # 1. プロジェクトルート(main.pyがある場所)を算出
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    # src/core -> src -> root
                    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
                    main_script_path = os.path.join(project_root, "clip_watcher.py")

                    # 2. activate.bat の場所を探索する
                    # 優先度1: 現在実行中のPython (sys.executable) と同じ階層にある Scripts/activate.bat
                    # (venv環境で実行していればこれが最も確実)
                    current_python_dir = os.path.dirname(sys.executable)
                    activate_candidates = [
                        os.path.join(current_python_dir, "activate.bat"), # Scriptsフォルダの中にいる場合
                        os.path.join(current_python_dir, "Scripts", "activate.bat"), # python.exeの親がルートの場合
                        os.path.join(project_root, "venv", "Scripts", "activate.bat"), # 一般的な名前 venv
                        os.path.join(project_root, ".venv", "Scripts", "activate.bat"), # 一般的な名前 .venv
                        os.path.join(project_root, "env", "Scripts", "activate.bat") # 一般的な名前 env
                    ]

                    final_activate_path = None
                    for path in activate_candidates:
                        if os.path.exists(path):
                            final_activate_path = path
                            break
                    
                    # 3. バッチファイルの内容を作成
                    script_content = '@echo off\n'
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
                self.show_error_message("Startup Error", f"Failed to manage startup script: {e}")

    def on_toggle_history_sort(self):
        """Toggles the history sort order and refreshes the GUI."""
        self.history_sort_ascending = not self.history_sort_ascending
        
        if self.history_sort_ascending:
            self.gui.sort_button.config(text=self.translator("sort_asc_button"))
        else:
            self.gui.sort_button.config(text=self.translator("sort_desc_button"))

        self.update_gui(self.monitor.last_clipboard_data, self.monitor.get_history())
        print(f"History sort order set to {'ascending' if self.history_sort_ascending else 'descending'}")

    def open_settings_window(self):
        self.create_toplevel(SettingsWindow, self.settings_manager)

    def create_toplevel(self, ToplevelClass, *args, **kwargs):
        toplevel_window = ToplevelClass(self.master, self, *args, **kwargs)
        
        # ToplevelClass might have a wait_window(), so the window could be destroyed
        # by the time we get here. Check if it still exists.
        if toplevel_window.winfo_exists():
            if self.settings_manager.get_setting("always_on_top", False):
                toplevel_window.attributes("-topmost", True)
            toplevel_window.transient(self.master)
            
        return toplevel_window

    def show_error_message(self, title, message):
        messagebox.showerror(title, message)

    def stop_monitor(self):
        self.monitor.stop()

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
