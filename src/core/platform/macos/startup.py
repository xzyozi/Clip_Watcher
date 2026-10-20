"""src/core/platform/macos/startup.py

macOS 用の LaunchAgents plist を用いたログイン時自動起動管理実装。
"""

from __future__ import annotations

import logging
import plistlib
import sys
from pathlib import Path

from src.core.platform.startup_python import resolve_python_executable

logger = logging.getLogger(__name__)

_DEFAULT_PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
_DEFAULT_PLIST_PATH = _DEFAULT_PLIST_DIR / "com.clipwatcher.app.plist"


def _resolve_main_script_path() -> Path:
    """プロジェクトルートの clip_watcher.py パスを解決する。"""
    # src/core/platform/macos/startup.py -> src/core/platform/macos -> src/core/platform -> src/core -> src -> root
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "clip_watcher.py"
        if candidate.exists():
            return candidate
    return Path.cwd() / "clip_watcher.py"


class MacOSStartupController:
    """LaunchAgents plist を用いた macOS ログイン時自動起動管理。"""

    def __init__(
        self,
        plist_path: Path | str | None = None,
        python_executable: str | None = None,
        main_script: Path | str | None = None,
    ) -> None:
        self.plist_path = Path(plist_path) if plist_path else _DEFAULT_PLIST_PATH
        self.main_script = (
            Path(main_script) if main_script else _resolve_main_script_path()
        )
        # .venv があれば優先し、無ければ現在の Python で起動する（Issue #209）。
        self.python_executable = python_executable or resolve_python_executable(
            self.main_script.parent, ("bin/python",), sys.executable
        )

    def is_enabled(self) -> bool:
        """自動起動 plist が配置されているかを返す。"""
        return self.plist_path.exists()

    def enable(self) -> bool:
        """LaunchAgents に plist を作成して自動起動を有効化する。"""
        try:
            self.plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_content = {
                "Label": "com.clipwatcher.app",
                "ProgramArguments": [
                    str(self.python_executable),
                    str(self.main_script),
                ],
                "RunAtLoad": True,
                "ProcessType": "Interactive",
            }
            with open(self.plist_path, "wb") as f:
                plistlib.dump(plist_content, f)
            logger.info("macOS 自動起動 plist を作成しました: %s", self.plist_path)
            return True
        except Exception as e:
            logger.error("macOS 自動起動 plist の作成に失敗しました: %s", e)
            return False

    def disable(self) -> bool:
        """LaunchAgents の plist を削除して自動起動を無効化する。"""
        try:
            if self.plist_path.exists():
                self.plist_path.unlink()
                logger.info("macOS 自動起動 plist を削除しました: %s", self.plist_path)
            return True
        except Exception as e:
            logger.error("macOS 自動起動 plist の削除に失敗しました: %s", e)
            return False
