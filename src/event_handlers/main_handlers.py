import tkinter as tk
import tkinter.messagebox # Import messagebox
import tkinter.filedialog # Import filedialog
# Removed: import keyboard # No longer needed

# This module will contain functions or a class for event handling

# Example: A function to handle copying selected history
def handle_copy_selected_history(gui_instance, history_data, selected_index):
    try:
        selected_item_content = history_data[selected_index][0] # Get content from (content, is_pinned) tuple
        # Use tkinter's clipboard methods
        gui_instance.master.clipboard_clear()
        gui_instance.master.clipboard_append(selected_item_content)
        print(f"Copied from history (Tkinter): {selected_item_content[:50]}...")
    except IndexError:
        pass # No item selected

def handle_quit(monitor_callback, master):
    if monitor_callback:
        monitor_callback()
    master.quit()

def handle_clear_all_history(monitor_instance, gui_instance):
    # Clear history in the monitor
    monitor_instance.clear_history()
    # Update GUI to reflect cleared history
    gui_instance.update_clipboard_display("", []) # Clear current display and history list
    print("All history cleared.")

def handle_delete_selected_history(gui_instance, monitor_instance):
    try:
        selected_indices = gui_instance.history_listbox.curselection()
        if not selected_indices:
            print("No history item selected for deletion.")
            return

        # Convert tuple of indices to list and sort in descending order
        # to avoid issues when deleting items from a list while iterating.
        indices_to_delete = sorted(list(selected_indices), reverse=True)

        for index in indices_to_delete:
            monitor_instance.delete_history_item(index)

        # After deletion, update the GUI to reflect the new history
        # The monitor's _trigger_gui_update will handle the GUI update after deletion.
        print(f"Deleted {len(selected_indices)} selected history item(s).")

    except Exception as e:
        print(f"Error deleting selected history: {e}")

def handle_delete_all_unpinned_history(monitor_instance, gui_instance, master):
    print("DEBUG: handle_delete_all_unpinned_history called.") # Debug print
    # Confirm with user before deleting
    if tkinter.messagebox.askyesno(
        "確認 (Confirm)",
        "ピン留めされていないすべての履歴を削除しますか？\nこの操作は元に戻せません。",
        parent=master # Pass master as parent
    ):
        monitor_instance.delete_all_unpinned_history()
        # GUI update will be triggered by monitor_instance.delete_all_unpinned_history
        tkinter.messagebox.showinfo("完了", "ピン留めされていない履歴をすべて削除しました。", parent=master)
    else:
        tkinter.messagebox.showinfo("キャンセル", "操作をキャンセルしました。", parent=master)

def handle_copy_fixed_phrase(gui_instance, phrase):
    try:
        gui_instance.master.clipboard_clear()
        gui_instance.master.clipboard_append(phrase)
        print(f"Copied fixed phrase: {phrase[:50]}...")
    except Exception as e:
        print(f"Error copying fixed phrase: {e}")

def handle_always_on_top(master, always_on_top_var):
    # Toggle the always on top attribute of the master window
    master.attributes('-topmost', always_on_top_var.get())
    print(f"Always on Top set to: {always_on_top_var.get()}")

def handle_about():
    tkinter.messagebox.showinfo(
        "バージョン情報 (About)",
        "ClipWatcher\nバージョン: 0.1.0\n開発者: Gemini CLI Agent\n\nこのアプリケーションは、クリップボードの履歴を管理し、再利用を容易にするために開発されました。"
    )

def handle_how_to_use():
    tkinter.messagebox.showinfo(
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

def handle_export_history(monitor_instance):
    file_path = tkinter.filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="履歴をエクスポート (Export History)"
    )
    if file_path:
        try:
            history_content = monitor_instance.get_history() # This returns (content, is_pinned) tuples
            with open(file_path, "w", encoding="utf-8") as f:
                for item_tuple in history_content:
                    f.write(item_tuple[0] + "\n---\n") # Write only content
            tkinter.messagebox.showinfo("エクスポート完了", f"履歴を以下のファイルにエクスポートしました:\n{file_path}")
        except Exception as e:
            tkinter.messagebox.showerror("エクスポートエラー", f"履歴のエクスポート中にエラーが発生しました:\n{e}")

def handle_import_history(monitor_instance, gui_instance):
    file_path = tkinter.filedialog.askopenfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="履歴をインポート (Import History)"
    )
    if file_path:
        try:
            imported_history = []
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Split by the separator and clean up empty strings
                raw_items = content.split("---")
                imported_history = [item.strip() for item in raw_items if item.strip()]
            
            # Add imported history to the monitor's history
            monitor_instance.import_history(imported_history)
            
            # Update GUI (monitor's _trigger_gui_update will handle this)
            tkinter.messagebox.showinfo("インポート完了", f"履歴を以下のファイルからインポートしました:\n{file_path}")
        except Exception as e:
            tkinter.messagebox.showerror("インポートエラー", f"履歴のインポート中にエラーが発生しました:\n{e}")

def handle_search_history(search_query, monitor_instance, gui_instance):
    # This function is called when the search entry content changes.
    # It will filter the history displayed in the GUI.
    if search_query:
        filtered_history = monitor_instance.get_filtered_history(search_query)
        gui_instance.update_history_display(filtered_history)
    else:
        # If search query is empty, display full history
        gui_instance.update_history_display(monitor_instance.get_history())

def handle_pin_unpin_history(gui_instance, monitor_instance):
    try:
        selected_index = gui_instance.history_listbox.curselection()[0]
        # Get the actual item from the monitor's history based on the displayed order
        item_tuple = monitor_instance.get_history()[selected_index]
        content, is_pinned = item_tuple

        if is_pinned:
            monitor_instance.unpin_item(selected_index)
            print(f"Unpinned: {content[:50]}...")
        else:
            monitor_instance.pin_item(selected_index)
            print(f"Pinned: {content[:50]}...")
        
        # Monitor's pin/unpin methods will call _trigger_gui_update
    except IndexError:
        print("No history item selected for pin/unpin.")
    except Exception as e:
        print(f"Error pinning/unpinning history: {e}")

def handle_copy_selected_as_merged(gui_instance):
    try:
        selected_indices = gui_instance.history_listbox.curselection()
        if not selected_indices:
            print("No history items selected for merging.")
            return

        merged_content_parts = []
        # Get the actual history data from the monitor, not just the displayed text
        # The selected_indices are based on the displayed listbox, which corresponds
        # to the order in monitor_instance.history.
        # We need to get the content from the history_data (which is already sorted by pinned status)
        for index in selected_indices:
            # Ensure index is valid for history_data
            if 0 <= index < len(gui_instance.history_data):
                merged_content_parts.append(gui_instance.history_data[index][0]) # Get content part

        if merged_content_parts:
            merged_content = "\n".join(merged_content_parts) # Join with newline
            gui_instance.master.clipboard_clear()
            gui_instance.master.clipboard_append(merged_content)
            print(f"Copied merged content: {merged_content[:50]}...")
        else:
            print("No valid history items selected for merging.")

    except Exception as e:
        print(f"Error merging and copying selected history: {e}")

from src.gui.fixed_phrases_window import FixedPhrasesWindow # Import the new window class
from src.fixed_phrases_manager import FixedPhrasesManager # Import the manager

def handle_manage_fixed_phrases(master, fixed_phrases_manager):
    # Create and show the FixedPhrasesWindow
    fixed_phrases_window = FixedPhrasesWindow(master, fixed_phrases_manager)
    fixed_phrases_window.grab_set() # Make it modal
    master.wait_window(fixed_phrases_window)

def handle_set_theme(gui_instance, theme_name):
    '''
    Handles setting the theme for the application.
    '''
    gui_instance.apply_theme(theme_name)
    print(f"Theme set to: {theme_name}")
