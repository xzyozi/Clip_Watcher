class ClipWatcherError(Exception):
    """ClipWatcherアプリケーションの基本例外クラス"""
    pass

class ClipboardError(ClipWatcherError):
    """クリップボード操作に関連するエラー"""
    pass

class ConfigError(ClipWatcherError):
    """設定関連のエラー"""
    pass

class PhraseError(ClipWatcherError):
    """定型文関連のエラー"""
    pass
