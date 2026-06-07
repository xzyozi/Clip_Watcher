import importlib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DependencyStatus:
    """依存関係の状態を保持するデータクラス"""
    win32_available: bool = False

class DependencyChecker:
    """
    オプションの依存関係（例: win32clipboard）が利用可能かどうかを確認するクラス。
    """
    @staticmethod
    def check_dependencies() -> DependencyStatus:
        """
        すべてのオプション依存関係をチェックし、その利用可能性を含むステータスオブジェクトを返します。
        """
        status = DependencyStatus()

        # win32clipboardの利用可能性を確認
        try:
            importlib.import_module("win32clipboard")
            importlib.import_module("pywintypes")
            status.win32_available = True
            logger.info("win32clipboardモジュールは利用可能です。")
        except ImportError:
            status.win32_available = False
            logger.warning("win32clipboardモジュールが見つかりません。一部の機能が制限される可能性があります。")

        return status
