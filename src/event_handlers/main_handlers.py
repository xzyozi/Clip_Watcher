import tkinter as tk
from tkinter import messagebox
from src.gui.fixed_phrases_window import FixedPhrasesFrame # Changed from FixedPhrasesWindow
from src.fixed_phrases_manager import FixedPhrasesManager

def handle_about():
    messagebox.showinfo(
        "バージョン情報 (About)",
        "ClipWatcher\nバージョン: 0.1.0\n開発者: Gemini CLI Agent\n\nこのアプリケーションは、クリップボードの履歴を管理し、再利用を容易にするために開発されました。"
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
        print(f"Copied fixed phrase: {phrase[:50]}...")
    except Exception as e:
        print(f"Error copying fixed phrase: {e}")

# Removed handle_manage_fixed_phrases as it's no longer needed with tabbed fixed phrases
