"""src/utils/platform_utils.py

OSプラットフォーム固有のシステム情報・環境検知ユーティリティ。
"""

from __future__ import annotations

import subprocess
import sys


def is_macos_dark_mode() -> bool:
    """macOS のシステム外観がダークモードに設定されているかを判定する。

    macOS (darwin) 以外、またはコマンド実行に失敗した場合は False を返す。
    """
    if sys.platform != "darwin":
        return False

    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True,
            check=False,
            timeout=1,
        )
        return result.stdout.strip().lower() == "dark"
    except Exception:
        return False
