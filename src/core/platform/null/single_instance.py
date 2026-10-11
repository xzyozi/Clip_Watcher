"""src/core/platform/null/single_instance.py

非 Windows / ヘッドレス環境向けの Null（排他なし）単一インスタンス制御アダプター。
"""

from __future__ import annotations


class NullSingleInstanceController:
    """非対応環境向けのダミー多重起動制御。常にロック取得に成功する。"""

    def acquire(self) -> bool:
        return True

    def release(self) -> None:
        pass
