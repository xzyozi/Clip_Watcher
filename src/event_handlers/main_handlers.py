import tkinter as tk
from tkinter import messagebox
from src.gui.windows.fixed_phrases_window import FixedPhrasesFrame
from src.core.fixed_phrases_manager import FixedPhrasesManager
from src.core.config import defaults
import logging

from src.utils.error_handler import log_and_show_error

logger = logging.getLogger(__name__)

def handle_about():
    messagebox.showinfo(
        "バージョン情報 (About)",
        f"ClipWatcher\nバージョン: {defaults.APP_VERSION}\n開発者: xx\n\nこのアプリケーションは、クリップボードの履歴を管理し、再利用を容易にするために開発されました。"
    )

def handle_how_to_use():
    messagebox.showinfo(
        "使い方 (How to Use)",
        "ClipWatcherの基本的な使い方:\n\n" 
        "1. アプリケーションを起動すると、自動的にクリップボードの監視を開始します。\n"
        "2. 何かテキストをコピーすると、メインウィンドウの「Current Clipboard Content」に表示され、履歴リストに追加されます。\n"
        "3. 履歴リストの項目をダブルクリックするか、「Copy Selected to Clipboard」ボタンをクリックすると、その項目がクリップボードにコピーされます。\n"
        "4. メニューバーから様々な機能にアクセスできます。\n"
        "   - 「ファイル」メニュー: 定型文のコピー、アプリケーションの終了など。\n"
        "   - 「編集」メニュー: 履歴の削除など。\n"
        "   - 「表示」メニュー: ウィンドウの表示設定など。\n"
        "   - 「ヘルプ」メニュー: バージョン情報など。\n"
        "\nご不明な点があれば、[SPECIFICATION.md](SPECIFICATION.md) を参照してください。"
    )

def handle_copy_fixed_phrase(gui_instance, phrase):
    try:
        gui_instance.master.clipboard_clear()
        gui_instance.master.clipboard_append(phrase)
        logger.info(f"Copied fixed phrase: {phrase[:50]}...")
    except Exception as e:
        log_and_show_error("エラー",f"Error copying fixed phrase: {e}")

def handle_manage_fixed_phrases(master, fixed_phrases_manager):
    fixed_phrases_window = FixedPhrasesManager(master, fixed_phrases_manager)
    fixed_phrases_window.grab_set()
    master.wait_window(fixed_phrases_window)


def handle_show_schedule_helper_tool(app_instance):
    """ Switch to the Schedule Helper Tool tab in the main notebook """
    try:
        # The tab index should be 2 (0: Clipboard, 1: Fixed Phrases, 2: Schedule Helper)
        app_instance.gui.notebook.select(2)
        logger.info("Switched to Schedule Helper Tool tab.")
    except tk.TclError as e:
        logger.error(f"Failed to switch to Schedule Helper Tool tab. It might not exist. {e}")
    except Exception as e:
        log_and_show_error("エラー", f"An unexpected error occurred while switching tabs: {e}")
