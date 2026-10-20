from __future__ import annotations

import os
import sys

# プロジェクトのルートディレクトリを特定し、sys.pathに追加
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

MIN_PYTHON_VERSION = (3, 10)


def check_python_version(
    version_info: tuple[int, ...] | None = None,
) -> tuple[bool, str]:
    """Python バージョンが要件 (>= 3.10) を満たしているか検証する。"""
    target = version_info if version_info is not None else sys.version_info
    if target < MIN_PYTHON_VERSION:
        curr_ver = f"{target[0]}.{target[1]}.{target[2] if len(target) > 2 else 0}"
        min_ver = f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"
        msg = (
            f"Clip Watcher の実行には Python {min_ver} 以上が必要です。\n\n"
            f"現在のバージョン: Python {curr_ver} ({sys.executable})\n\n"
            "仮想環境 (.venv) をアクティベートして実行するか、Python 3.10 以降を使用してください。\n"
            "例: .venv/bin/python clip_watcher.py"
        )
        return False, msg
    return True, ""


def ensure_python_version() -> None:
    """Python バージョンを検証し、要件を満たさない場合は案内を出力して安全に終了する。"""
    ok, msg = check_python_version()
    if not ok:
        sys.stderr.write(f"[ERROR] {msg}\n")
        if sys.platform == "darwin":
            try:
                import subprocess

                applescript_msg = msg.replace('"', '\\"')
                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        f'display alert "Clip Watcher 起動エラー" message "{applescript_msg}" as critical',
                    ],
                    check=False,
                    timeout=5,
                )
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    ensure_python_version()

    from src.event_handlers import start_app

    start_app()
