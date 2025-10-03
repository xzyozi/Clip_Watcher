"""Application interface for type hints"""
from abc import ABC, abstractmethod

class BaseApplication(ABC):
    """アプリケーションのインターフェース定義"""
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
