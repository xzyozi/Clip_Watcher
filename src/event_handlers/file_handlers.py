import tkinter as tk
from tkinter import filedialog, messagebox

class FileEventHandlers:
    def __init__(self, app_instance):
        self.app = app_instance

    def handle_quit(self):
        self.app.stop_monitor()
        self.app.master.quit()

    def handle_export_history(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="履歴をエクスポート (Export History)"
        )
        if file_path:
            try:
                history_content = self.app.monitor.get_history()
                with open(file_path, "w", encoding="utf-8") as f:
                    for item_tuple in history_content:
                        f.write(item_tuple[0] + "\n---")
                messagebox.showinfo("エクスポート完了", f"履歴を以下のファイルにエクスポートしました:\n{file_path}")
            except Exception as e:
                messagebox.showerror("エクスポートエラー", f"履歴のエクスポート中にエラーが発生しました:\n{e}")

    def handle_import_history(self):
        file_path = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="履歴をインポート (Import History)"
        )
        if file_path:
            try:
                imported_history = []
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    raw_items = content.split("---")
                    imported_history = [item.strip() for item in raw_items if item.strip()]
                
                self.app.monitor.import_history(imported_history)
                messagebox.showinfo("インポート完了", f"履歴を以下のファイルからインポートしました:\n{file_path}")
            except Exception as e:
                messagebox.showerror("インポートエラー", f"履歴のインポート中にエラーが発生しました:\n{e}")
