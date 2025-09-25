import tkinter as tk
from tkinter import messagebox
import traceback
import logging

# このハンドラ専用のLoggerインスタンスを作成
logger = logging.getLogger("TkinterErrorHandler")

def global_exception_handler(exc, val, tb):
    """
    Tkinterの未補足例外を処理するグローバルハンドラ。
    ユーザーにエラーメッセージを表示し、詳細をログに記録する。
    """
    # スタックトレースを整形してログに出力
    error_message = "".join(traceback.format_exception(exc, val, tb))
    logger.error(f"Unhandled exception in Tkinter callback:\n{error_message}")

    # ユーザーにシンプルなエラーメッセージを表示
    messagebox.showerror("Application Error", f"An unexpected error occurred: {val}\n\nDetails have been logged.")

def setup_global_error_handler():
    """
    Tkinterのデフォルト例外ハンドラをカスタムハンドラで上書きする。
    """
    tk.Tk.report_callback_exception = global_exception_handler
    logging.getLogger(__name__).info("Global Tkinter error handler has been set up.")

