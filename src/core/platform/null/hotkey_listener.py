"""src/core/platform/null/hotkey_listener.py

非 Windows / ヘッドレス環境向けの Null（安全なダミー）ホットキーリスナー。
設定画面での保存処理を妨げないよう、登録成功 (True) を返す。
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class NullHotkeyListener:
    """非対応環境向けのダミーホットキーリスナー。

    設定保存時のバリデーションを通過させるため、登録要求に対して常に True を返す。
    """

    def start(self, modifiers: int, vk_code: int) -> bool:
        return True

    def start_many(self, registrations: Iterable[Any]) -> bool:
        return True

    def stop(self) -> None:
        pass
