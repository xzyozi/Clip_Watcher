import logging
import tkinter as tk
from typing import TYPE_CHECKING

from typing_extensions import Self

from src.gui.theme_manager import ThemeManager
from src.utils.error_handler import log_and_show_error
from src.utils.i18n import Translator

from .clipboard_monitor import ClipboardMonitor
from .config.app_status import AppStatus
from .config.settings_manager import SettingsManager
from .dependency_checker import DependencyChecker
from .event_dispatcher import EventDispatcher
from .exceptions import ConfigError
from .fixed_phrases_manager import FixedPhrasesManager
from .plugin_manager import PluginManager

if TYPE_CHECKING:
    from src.core.app_main import MainApplication

logger = logging.getLogger(__name__)

class ApplicationBuilder:
    """アプリケーションの構築を担当するクラス"""

    def __init__(self) -> None:
        self.settings_manager: SettingsManager | None = None
        self.monitor: ClipboardMonitor | None = None
        self.fixed_phrases_manager: FixedPhrasesManager | None = None
        self.plugin_manager: PluginManager | None = None
        self.event_dispatcher: EventDispatcher | None = None
        self.theme_manager: ThemeManager | None = None

        self.translator: Translator | None = None
        self.app_status: AppStatus | None = None

    def with_event_dispatcher(self) -> Self:
        """イベントディスパッチャの初期化"""
        try:
            self.event_dispatcher = EventDispatcher()
            logger.info("イベントディスパッチャを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(title="エラー", message=f"イベントディスパッチャの初期化に失敗: {str(e)}")
            raise ConfigError(f"イベントディスパッチャの初期化に失敗しました: {str(e)}") from e

    def with_dependency_check(self) -> Self:
        """依存関係のチェック"""
        try:
            dependency_status = DependencyChecker.check_dependencies()
            self.app_status = AppStatus(dependencies=dependency_status)
            logger.info("依存関係のチェックが完了しました")
            return self
        except Exception as e:
            log_and_show_error(title="エラー", message=f"依存関係のチェック中にエラーが発生: {str(e)}")
            raise ConfigError(f"依存関係のチェックに失敗しました: {str(e)}") from e

    def with_settings(self, settings_file_path: str = "settings.json") -> Self:
        """設定マネージャーの初期化"""
        if not self.event_dispatcher:
            raise ConfigError("イベントディスパッチャが初期化されていません")
        try:
            self.settings_manager = SettingsManager(self.event_dispatcher, settings_file_path)
            logger.info("設定マネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(title="エラー", message=f"設定マネージャーの初期化に失敗: {str(e)}")
            raise ConfigError(f"設定の読み込みに失敗しました: {str(e)}") from e

    def with_translator(self) -> Self:
        """翻訳サービスの初期化"""
        if not self.settings_manager:
            raise ConfigError("設定マネージャーが初期化されていません")
        try:
            self.translator = Translator(self.settings_manager)
            logger.info("翻訳サービスを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(title="エラー", message=f"翻訳サービスの初期化に失敗: {str(e)}")
            raise ConfigError(f"翻訳サービスの初期化に失敗しました: {str(e)}") from e

    def with_theme_manager(self, root: tk.Tk) -> Self:
        """テーママネージャーの初期化"""
        try:
            self.theme_manager = ThemeManager(root)
            logger.info("テーママネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(title="エラー", message=f"テーママネージャーの初期化に失敗: {str(e)}")
            raise ConfigError(f"テーママネージャーの初期化に失敗しました: {str(e)}") from e

    def with_clipboard_monitor(self, master: tk.Tk, history_file_path: str) -> Self:
        """クリップボードモニターの初期化"""
        if not self.event_dispatcher or not self.app_status:
            raise ConfigError("イベントディスパッチャまたはアプリケーションステータスが初期化されていません")

        try:
            win32_available = self.app_status.dependencies.win32_available
            self.monitor = ClipboardMonitor(master, self.event_dispatcher, history_file_path, win32_available)
            logger.info("クリップボードモニターを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(title="エラー", message=f"クリップボードモニターの初期化に失敗: {str(e)}")
            raise ConfigError(f"クリップボードモニターの初期化に失敗しました: {str(e)}") from e

    def with_fixed_phrases_manager(self, file_path: str = "fixed_phrases.json") -> Self:
        """定型文マネージャーの初期化"""
        try:
            self.fixed_phrases_manager = FixedPhrasesManager(file_path)
            logger.info("定型文マネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(title="エラー", message=f"定型文マネージャーの初期化に失敗: {str(e)}")
            raise ConfigError(f"定型文マネージャーの初期化に失敗しました: {str(e)}") from e

    def with_plugin_manager(self) -> Self:
        """プラグインマネージャーの初期化"""
        try:
            self.plugin_manager = PluginManager()
            logger.info("プラグインマネージャーを初期化しました")
            return self
        except Exception as e:
            log_and_show_error(title="エラー", message=f"プラグインマネージャーの初期化に失敗: {str(e)}")
            raise ConfigError(f"プラグインマネージャーの初期化に失敗しました: {str(e)}") from e



    def build(self, master: tk.Tk) -> MainApplication:
        """アプリケーションのビルド"""
        if not all([self.settings_manager, self.monitor, self.fixed_phrases_manager, self.plugin_manager, self.event_dispatcher, self.theme_manager, self.translator, self.app_status]):
            raise ConfigError("必要なコンポーネントが初期化されていません")

        try:
            from src.core.app_main import MainApplication
            app = MainApplication(
                master=master,
                settings_manager=self.settings_manager, # type: ignore
                monitor=self.monitor, # type: ignore
                fixed_phrases_manager=self.fixed_phrases_manager, # type: ignore
                plugin_manager=self.plugin_manager, # type: ignore
                event_dispatcher=self.event_dispatcher, # type: ignore
                theme_manager=self.theme_manager, # type: ignore

                translator=self.translator, # type: ignore
                app_status=self.app_status # type: ignore
            )
            logger.info("アプリケーションのビルドが完了しました")

            # Load settings and notify all components
            self.settings_manager.load_and_notify() # type: ignore

            # Signal that the application is ready
            app.on_ready()

            return app
        except Exception as e:
            log_and_show_error(title="エラー", message=f"アプリケーションのビルドに失敗: {str(e)}")
            raise ConfigError(f"アプリケーションの構築に失敗しました: {str(e)}") from e
