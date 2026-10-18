"""src/core/platform/windows/startup.py

Windows 用のレジストリ（HKCU\\...\\Run）を用いたログオン時自動起動管理実装。
バッチファイル（.bat）を使用せず、コマンドインジェクションを防止する。
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "ClipWatcher"


def _resolve_main_script_path() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "clip_watcher.py"
        if candidate.exists():
            return candidate
    return Path.cwd() / "clip_watcher.py"


def _resolve_pythonw_executable() -> str:
    """可能ならコンソールウィンドウの出ない pythonw.exe を返す。"""
    exe = sys.executable
    if "python.exe" in exe.lower():
        pythonw = exe.lower().replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw):
            return pythonw
    return exe


def _remove_legacy_batch_file() -> None:
    """旧バージョンで作成された可能性のある Startup\\ClipWatcher.bat をクリーンアップする。"""
    try:
        app_data = os.environ.get("APPDATA")
        if not app_data:
            return
        legacy_bat = (
            Path(app_data)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
            / "ClipWatcher.bat"
        )
        if legacy_bat.exists():
            legacy_bat.unlink()
            logger.info(
                "レガシーなスタートアップバッチファイルを削除しました: %s", legacy_bat
            )
    except Exception as e:
        logger.debug("レガシーバッチファイルの削除中にエラー: %s", e)


class WindowsStartupController:
    """Windows レジストリを用いたログオン時自動起動管理。"""

    def __init__(
        self,
        python_executable: str | None = None,
        main_script: Path | str | None = None,
    ) -> None:
        self.python_executable = python_executable or _resolve_pythonw_executable()
        self.main_script = (
            Path(main_script) if main_script else _resolve_main_script_path()
        )

    def is_enabled(self) -> bool:
        """レジストリに自動起動設定が存在するかを返す。"""
        if sys.platform != "win32":
            return False

        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_READ
            ) as key:
                val, _ = winreg.QueryValueEx(key, _VALUE_NAME)
                return bool(val)
        except (FileNotFoundError, OSError):
            return False
        except Exception as e:
            logger.debug("レジストリの読み込みに失敗しました: %s", e)
            return False

    def enable(self) -> bool:
        """レジストリに登録して自動起動を有効化する。"""
        if sys.platform != "win32":
            return False

        try:
            import winreg

            command = f'"{self.python_executable}" "{self.main_script}"'
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH) as key:
                winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, command)

            logger.info("Windows レジストリに自動起動を登録しました: %s", command)
            _remove_legacy_batch_file()
            return True
        except Exception as e:
            logger.error("Windows レジストリへの自動起動登録に失敗しました: %s", e)
            return False

    def disable(self) -> bool:
        """レジストリから自動起動設定を削除する。"""
        if sys.platform != "win32":
            return False

        try:
            import winreg

            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.DeleteValue(key, _VALUE_NAME)
                    logger.info("Windows レジストリから自動起動を削除しました。")
            except FileNotFoundError:
                pass

            _remove_legacy_batch_file()
            return True
        except Exception as e:
            logger.error("Windows レジストリからの自動起動削除に失敗しました: %s", e)
            return False
