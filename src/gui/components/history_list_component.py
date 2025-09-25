import tkinter as tk
from tkinter import ttk, messagebox

class HistoryListComponent(ttk.Frame):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.setup_gui()
        
    def setup_gui(self):
        # リストビューの作成
        columns = ('Time', 'Content')
        self.list = ttk.Treeview(self, columns=columns, show='headings', selectmode='extended')
        
        # 列の設定
        self.list.heading('Time', text='時刻')
        self.list.heading('Content', text='内容')
        self.list.column('Time', width=100)
        self.list.column('Content', width=400)
        
        # スクロールバーの設定
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.list.yview)
        self.list.configure(yscrollcommand=scrollbar.set)
        
        # 配置
        self.list.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        # グリッドの設定
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # コンテキストメニューのバインド
        self.list.bind('<Button-3>', self.show_context_menu)
        self.list.bind('<Double-Button-1>', lambda e: self.copy_selected())
    
    def show_context_menu(self, event):
        selection = self.list.selection()
        if not selection:
            return
            
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(label="コピー", command=self.copy_selected)
        context_menu.add_command(label="クイックタスクとして開く", command=self.create_quick_task)
        context_menu.add_separator()
        context_menu.add_command(label="削除", command=self.delete_selected)
        
        context_menu.post(event.x_root, event.y_root)
    
    def create_quick_task(self):
        """選択された履歴項目からクイックタスクを作成"""
        selection = self.list.selection()
        if not selection:
            return
            
        tasks = []
        for item in selection:
            content = self.list.item(item)['values'][1]
            tasks.append(content)
            
        if tasks:
            from ..quick_task_dialog import QuickTaskDialog
            dialog = QuickTaskDialog(self, tasks)
    
    def copy_selected(self):
        """選択された項目をクリップボードにコピー"""
        selection = self.list.selection()
        if not selection:
            return
            
        item = selection[0]
        content = self.list.item(item)['values'][1]
        
        self.master.clipboard_clear()
        self.master.clipboard_append(content)
        
    def delete_selected(self):
        """選択された項目を削除"""
        selection = self.list.selection()
        if not selection:
            return
            
        if messagebox.askyesno("確認", "選択した項目を削除しますか？"):
            for item in selection:
                self.list.delete(item)
                
    def clear(self):
        """履歴をクリア"""
        for item in self.list.get_children():
            self.list.delete(item)
            
    def add_item(self, time, content):
        """履歴項目を追加"""
        self.list.insert('', 0, values=(time, content))
        
    def get_all_items(self):
        """すべての履歴項目を取得"""
        items = []
        for item in self.list.get_children():
            time, content = self.list.item(item)['values']
            items.append((time, content))
        return items