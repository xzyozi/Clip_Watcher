"""Application interface for type hints"""
from abc import ABC, abstractmethod
import tkinter as tk
from src.settings_manager import SettingsManager
from src.clipboard_monitor import ClipboardMonitor
from src.fixed_phrases_manager import FixedPhrasesManager

class Application(ABC):
    """アプリケーションのインターフェース定義"""
    def __init__(self, master: tk.Tk, settings_manager: SettingsManager,
                 monitor: ClipboardMonitor, fixed_phrases_manager: FixedPhrasesManager):
        self.master = master
        self.settings_manager = settings_manager
        self.monitor = monitor
        self.fixed_phrases_manager = fixed_phrases_manager

    @abstractmethod
    def open_settings_window(self) -> None:
        """設定ウィンドウを開く"""
        pass

    @abstractmethod
    def stop_monitor(self) -> None:
        """モニターを停止する"""
        pass

    @abstractmethod
    def on_closing(self) -> None:
        """アプリケーション終了時の処理"""
        pass
