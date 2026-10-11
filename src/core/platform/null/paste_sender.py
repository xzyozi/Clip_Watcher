"""src/core/platform/null/paste_sender.py

非 Windows / ヘッドレス環境向けの Null（キーストローク送信なし）ペースト送信アダプター。
"""

from __future__ import annotations


class NullPasteSender:
    """非対応環境向けのダミーペースト送信アダプター。"""

    def are_modifiers_released(self) -> bool:
        return True

    def paste_active_window(self) -> bool:
        return False
