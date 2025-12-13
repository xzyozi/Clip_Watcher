import tkinter as tk
from tkinter import ttk
from src.gui.base.base_toplevel_gui import BaseToplevelGUI

class QuickTaskDialog(BaseToplevelGUI):
    def __init__(self, master, app_instance, tasks=None):
        super().__init__(master, app_instance)
        self.title("クイックタスク")
        self.tasks = tasks or []
        self.task_vars = []
        self._setup_gui()

    def _setup_gui(self):
        # メインフレーム
        main_frame = ttk.Frame(self)
        main_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # タスクリスト
        self.task_list = ttk.Treeview(main_frame, columns=('Content',), show='headings', selectmode='browse')
        self.task_list.heading('Content', text='内容')
        self.task_list.pack(expand=True, fill='both', side='left')

        # スクロールバー
        scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=self.task_list.yview)
        scrollbar.pack(side='right', fill='y')
        self.task_list.configure(yscrollcommand=scrollbar.set)
        self.task_list.bind("<Double-1>", lambda event: self._copy_selected())

        # ボタンフレーム
        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=(0, 10))

        # コピーボタン
        copy_btn = ttk.Button(button_frame, text="コピー", command=self._copy_selected)
        copy_btn.pack(side='left', padx=5)

        # 閉じるボタン
        close_btn = ttk.Button(button_frame, text="閉じる", command=self.destroy)
        close_btn.pack(side='right', padx=5)

        self._populate_tasks()

    def _populate_tasks(self):
        """
        quick_listを作成する
        渡されたタスクリストをTreeviewに表示します。
        このメソッドは、改行コードを含むタスクを自動的に分割し、
        それぞれを個別の行として描画する責務を持ちます。
        """
        # 既存のリストアイテムをすべてクリアします。
        # これにより、ダイアログが再利用された場合でもリストが重複することはありません。
        for item in self.task_list.get_children():
            self.task_list.delete(item)

        # 最終的にリストに表示するためのタスクを格納する新しいリストを初期化します。
        processed_tasks = []

        # self.tasks には、外部から渡されたタスクのリストが格納されています。
        # 例: ["タスクA\nタスクB", "タスクC"]
        for task_item in self.tasks:
            # 各タスク項目を改行文字 ("\n") で分割します。
            # これにより、"タスクA\nタスクB" は ["タスクA", "タスクB"] のようなリストになります。
            # 改行が含まれていないタスクは、要素が1つのリストになります (例: ["タスクC"])。
            lines = task_item.split('\n')
            
            # 分割して得られた行のリストを processed_tasks に追加します。
            # extend を使用することで、リストがネストされず、すべての行がフラットなリストに格納されます。
            processed_tasks.extend(lines)

        # 処理済みのタスクリスト（すべての行が個別の要素になっている）をループ処理します。
        for task in processed_tasks:
            # 空白行（例：連続した改行によって生じる）はリストに追加しないようにします。
            # strip() で前後の空白を除去し、空文字列でないことを確認します。
            if task.strip():
                # Treeviewウィジェットの末尾にタスクを一件ずつ挿入します。
                # これにより、ユーザーはUI上で各タスクを個別の行として見ることができます。
                self.task_list.insert('', 'end', values=(task.strip(),))

    def _copy_selected(self):
        """選択されたタスクをコピーして削除"""
        selection = self.task_list.selection()
        if not selection:
            return

        # 選択された項目の内容を取得
        item = self.task_list.item(selection[0])
        content = item['values'][0]

        # クリップボードにコピー
        self.clipboard_clear()
        self.clipboard_append(content)

        # 項目を削除
        self.task_list.delete(selection[0])

        # すべてのタスクが完了したら自動的にダイアログを閉じる
        if not self.task_list.get_children():
            self.destroy()

    def add_tasks(self, tasks):
        """タスクを追加"""
        for task in tasks:
            self.task_list.insert('', 'end', values=(task,))

    def get_remaining_tasks(self):
        """残りのタスクを取得"""
        return [self.task_list.item(item)['values'][0] for item in self.task_list.get_children()]