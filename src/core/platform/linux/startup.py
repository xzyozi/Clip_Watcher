"""src/core/platform/linux/startup.py

Linux 用の XDG Autostart (.desktop) を用いた自動起動管理実装。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
_DEFAULT_DESKTOP_PATH = _DEFAULT_AUTOSTART_DIR / "clipwatcher.desktop"


def _resolve_main_script_path() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "clip_watcher.py"
        if candidate.exists():
            return candidate
    return Path.cwd() / "clip_watcher.py"


class LinuxStartupController:
    """XDG Autostart を用いた Linux 自動起動管理。"""

    def __init__(
        self,
        desktop_path: Path | str | None = None,
        python_executable: str | None = None,
        main_script: Path | str | None = None,
    ) -> None:
        self.desktop_path = (
            Path(desktop_path) if desktop_path else _DEFAULT_DESKTOP_PATH
        )
        self.python_executable = python_executable or sys.executable
        self.main_script = (
            Path(main_script) if main_script else _resolve_main_script_path()
        )

    def is_enabled(self) -> bool:
        """autostart desktop ファイルが存在するかを返す。"""
        return self.desktop_path.exists()

    def enable(self) -> bool:
        """autostart ディレクトリに desktop ファイルを作成して自動起動を有効化する。"""
        try:
            self.desktop_path.parent.mkdir(parents=True, exist_ok=True)
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Version=1.0\n"
                "Name=ClipWatcher\n"
                "Comment=Clipboard Manager\n"
                f'Exec="{self.python_executable}" "{self.main_script}"\n'
                "Terminal=false\n"
                "Categories=Utility;\n"
            )
            self.desktop_path.write_text(content, encoding="utf-8")
            logger.info(
                "Linux 自動起動 desktop ファイルを作成しました: %s", self.desktop_path
            )
            return True
        except Exception as e:
            logger.error("Linux 自動起動 desktop ファイルの作成に失敗しました: %s", e)
            return False

    def disable(self) -> bool:
        """autostart の desktop ファイルを削除して自動起動を無効化する。"""
        try:
            if self.desktop_path.exists():
                self.desktop_path.unlink()
                logger.info(
                    "Linux 自動起動 desktop ファイルを削除しました: %s",
                    self.desktop_path,
                )
            return True
        except Exception as e:
            logger.error("Linux 自動起動 desktop ファイルの削除に失敗しました: %s", e)
            return False
