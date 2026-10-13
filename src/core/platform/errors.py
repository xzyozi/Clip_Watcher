"""src/core/platform/errors.py

プラットフォーム抽象レイヤーの例外階層。

非対応環境では、成功を装う Null 実装ではなく、これらの例外で明示的に失敗を通知する。
呼び出し側は機能単位で捕捉し、警告ログ等で明示的に縮退する。
"""

from __future__ import annotations

from src.core.bootstrap.exceptions import ClipWatcherError


class PlatformError(ClipWatcherError):
    """プラットフォーム層の共通親例外。"""


class UnsupportedFeatureError(PlatformError):
    """現在のOSで非対応の機能を要求した。

    Attributes:
        feature: 要求された機能名（例: ``"sound_player"``）。
        platform: 現在のプラットフォーム識別子（``sys.platform``）。
    """

    def __init__(self, feature: str, platform: str) -> None:
        self.feature = feature
        self.platform = platform
        super().__init__(
            f"この環境 ({platform}) では機能 '{feature}' はサポートされていません。"
        )


class SingleInstanceError(PlatformError):
    """多重起動防止の排他ロック取得 API が失敗した。

    他のインスタンスが起動中であること（``acquire()`` が False を返す）とは区別する。
    """
