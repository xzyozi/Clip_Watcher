from __future__ import annotations

from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from .base_event_handler import BaseEventHandler

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication
    from src.core.event_dispatcher import EventDispatcher


class FileEventHandlers(BaseEventHandler):
    def __init__(self, app_instance: BaseApplication, event_dispatcher: EventDispatcher) -> None:
        self.app = app_instance
        super().__init__(event_dispatcher)

    def _register_handlers(self) -> None:
        self.subscribe("FILE_QUIT", self.handle_quit)
        self.subscribe("FILE_EXPORT_HISTORY", self.handle_export_history)
        self.subscribe("FILE_IMPORT_HISTORY", self.handle_import_history)

    def handle_quit(self) -> None:
        self.app.on_closing()

    def handle_export_history(self) -> None:
        file_path: str = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="履歴をエクスポート (Export History)"
        )
        if file_path:
            try:
                history_content: list[tuple[str, bool, float]] = self.app.monitor.get_history() # type: ignore
                with open(file_path, "w", encoding="utf-8") as f:
                    for item_tuple in history_content:
                        f.write(item_tuple[0] + "\n---")
                messagebox.showinfo("エクスポート完了", f"履歴を以下のファイルにエクスポートしました:\n{file_path}")
            except Exception as e:
                messagebox.showerror("エクスポートエラー", f"履歴のエクスポート中にエラーが発生しました:\n{e}")

    def handle_import_history(self) -> None:
        file_path: str = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="履歴をインポート (Import History)"
        )
        if file_path:
            try:
                imported_history: list[str] = []
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    raw_items = content.split("---")
                    imported_history = [item.strip() for item in raw_items if item.strip()]

                self.app.monitor.import_history(imported_history) # type: ignore
                messagebox.showinfo("インポート完了", f"履歴を以下のファイルからインポートしました:\n{file_path}")
            except Exception as e:
                messagebox.showerror("インポートエラー", f"履歴のインポート中にエラーが発生しました:\n{e}")
