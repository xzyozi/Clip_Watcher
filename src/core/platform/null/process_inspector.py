"""src/core/platform/null/process_inspector.py

非 Windows / ヘッドレス環境向けの Null（安全なダミー）プロセス検査アダプター。
"""

from __future__ import annotations


class NullProcessInspector:
    """非対応環境向けのダミープロセス検査クラス。常に None を返す。"""

    def get_active_process_name(self) -> str | None:
        return None
