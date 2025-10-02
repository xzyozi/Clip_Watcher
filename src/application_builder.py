from typing import Optional, TYPE_CHECKING
import tkinter as tk
from src.clipboard_monitor import ClipboardMonitor
from src.settings_manager import SettingsManager
from src.fixed_phrases_manager import FixedPhrasesManager
from src.exceptions import ConfigError
from src.event_handlers.history_handlers import HistoryEventHandlers
from src.event_handlers.file_handlers import FileEventHandlers
from src.event_handlers.settings_handlers import SettingsEventHandlers
from src.plugin_manager import PluginManager
from src.event_dispatcher import EventDispatcher
import logging
from src.utils.error_handler import log_and_show_error

if TYPE_CHECKING:
    from src.base_application import BaseApplication

logger = logging.getLogger(__name__)

class ApplicationBuilder:
    """アプリケーションの構築を担当するクラス"""
    
    def __init__(self):
        self.settings_manager: Optional[SettingsManager] = None
        self.monitor: Optional[ClipboardMonitor] = None
        self.fixed_phrases_manager: Optional[FixedPhrasesManager] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.event_dispatcher: Optional[EventDispatcher] = None
        
    def with_settings(self, settings_file_path: str = "settings.json") -> 'ApplicationBuilder':
        """設定マネージャーの初期化"""
        try:
            self.settings_manager = SettingsManager(settings_file_path)
            logger.info("設定マネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(f"設定マネージャーの初期化に失敗: {str(e)}")
            raise ConfigError(f"設定の読み込みに失敗しました: {str(e)}")

    def with_clipboard_monitor(self, master: tk.Tk, history_file_path: str) -> 'ApplicationBuilder':
        """クリップボードモニターの初期化"""
        if not self.settings_manager:
            raise ConfigError("設定マネージャーが初期化されていません")
        
        try:
            self.monitor = ClipboardMonitor(
                master,
                self.settings_manager,
                history_file_path,
                self.settings_manager.get_setting("history_limit"),
                self.settings_manager.get_setting("excluded_apps")
            )
            logger.info("クリップボードモニターを初期化しました")
            return self
        except Exception as e:
            log_and_show_error("エラー", f"クリップボードモニターの初期化に失敗: {str(e)}")
            raise ConfigError(f"クリップボードモニターの初期化に失敗しました: {str(e)}")

    def with_fixed_phrases_manager(self, file_path: str = "fixed_phrases.json") -> 'ApplicationBuilder':
        """定型文マネージャーの初期化"""
        try:
            self.fixed_phrases_manager = FixedPhrasesManager(file_path)
            logger.info("定型文マネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error("エラー", f"定型文マネージャーの初期化に失敗: {str(e)}")
            raise ConfigError(f"定型文マネージャーの初期化に失敗しました: {str(e)}")

    def with_plugin_manager(self) -> 'ApplicationBuilder':
        """プラグインマネージャーの初期化"""
        try:
            self.plugin_manager = PluginManager()
            logger.info("プラグインマネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error("エラー", f"プラグインマネージャーの初期化に失敗: {str(e)}")
            raise ConfigError(f"プラグインマネージャーの初期化に失敗しました: {str(e)}")

    def with_event_dispatcher(self) -> 'ApplicationBuilder':
        """イベントディスパッチャの初期化"""
        try:
            self.event_dispatcher = EventDispatcher()
            logger.info("イベントディスパッチャを初期化しました")
            return self
        except Exception as e:
            log_and_show_error("エラー", f"イベントディスパッチャの初期化に失敗: {str(e)}")
            raise ConfigError(f"イベントディスパッチャの初期化に失敗しました: {str(e)}")

    def build(self, master: tk.Tk) -> 'BaseApplication':
        """アプリケーションのビルド"""
        if not all([self.settings_manager, self.monitor, self.fixed_phrases_manager, self.plugin_manager, self.event_dispatcher]):
            raise ConfigError("必要なコンポーネントが初期化されていません")
            
        
        from clip_watcher import Application as MainApplication  # 具体的な実装をインポート
        
        try:
            app = MainApplication(
                master=master,
                settings_manager=self.settings_manager,
                monitor=self.monitor,
                fixed_phrases_manager=self.fixed_phrases_manager,
                plugin_manager=self.plugin_manager,
                event_dispatcher=self.event_dispatcher
            )
            logger.info("アプリケーションのビルドが完了しました")
            return app
        except Exception as e:
            log_and_show_error("エラー", f"アプリケーションのビルドに失敗: {str(e)}")
            raise ConfigError(f"アプリケーションの構築に失敗しました: {str(e)}")
