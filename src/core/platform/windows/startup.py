"""src/core/platform/windows/startup.py

Windows 用の Startup フォルダのショートカット（.lnk）を用いたログオン時自動起動管理実装。

``.bat`` と異なり、``.lnk`` は ``TargetPath`` と ``Arguments`` が別フィールドで、
シェルによる文字列解釈を伴わないため、コマンドインジェクションを防止できる。
macOS（LaunchAgents plist）・Linux（XDG autostart）と同様に、
所定の場所へファイルを置く方式にそろえている（Issue #209）。

旧バージョンが作成した ``.bat`` と、レジストリ（HKCU\\...\\Run）の登録値は
有効化・無効化の際に削除する（移行用）。レジストリへの新規登録は行わない。
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from src.core.platform.startup_python import resolve_python_executable

logger = logging.getLogger(__name__)

_LEGACY_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_LEGACY_VALUE_NAME = "ClipWatcher"
_SHORTCUT_NAME = "ClipWatcher.lnk"
_LEGACY_BATCH_NAME = "ClipWatcher.bat"


def _resolve_main_script_path() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "clip_watcher.py"
        if candidate.exists():
            return candidate
    return Path.cwd() / "clip_watcher.py"


def _fallback_pythonw_executable() -> str:
    """現在の Python と同じ場所の pythonw.exe（コンソールが出ない）を返す。無ければ現在の Python。"""
    exe = sys.executable
    if "python.exe" in exe.lower():
        pythonw = exe.lower().replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw):
            return pythonw
    return exe


def _startup_folder() -> Path | None:
    """ユーザーの Startup フォルダを返す。APPDATA が未定義なら None。"""
    app_data = os.environ.get("APPDATA")
    if not app_data:
        return None
    return (
        Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    )


def _legacy_batch_paths() -> list[Path]:
    """旧バージョンが ``ClipWatcher.bat`` を作成していた可能性のある場所を返す。"""
    app_data = os.environ.get("APPDATA")
    if not app_data:
        return []
    startup = _startup_folder()
    paths = [Path(app_data) / "Microsoft" / "Windows" / "Startup" / _LEGACY_BATCH_NAME]
    if startup is not None:
        paths.append(startup / _LEGACY_BATCH_NAME)
    return paths


def _remove_legacy_batch_file() -> None:
    """旧バージョンで作成された可能性のある ClipWatcher.bat を削除する。"""
    for legacy_bat in _legacy_batch_paths():
        try:
            if legacy_bat.exists():
                legacy_bat.unlink()
                logger.info(
                    "レガシーなスタートアップバッチファイルを削除しました: %s",
                    legacy_bat,
                )
        except Exception as e:
            logger.debug("レガシーバッチファイルの削除中にエラー: %s", e)


def _remove_legacy_registry_value() -> None:
    """旧バージョンが登録したレジストリの自動起動値を削除する（移行用）。"""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _LEGACY_RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, _LEGACY_VALUE_NAME)
            logger.info("レガシーなレジストリの自動起動値を削除しました。")
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.debug("レガシーなレジストリ値の削除中にエラー: %s", e)


def _remove_legacy_entries() -> None:
    _remove_legacy_batch_file()
    _remove_legacy_registry_value()


class WindowsStartupController:
    """Startup フォルダのショートカット（.lnk）を用いたログオン時自動起動管理。"""

    def __init__(
        self,
        python_executable: str | None = None,
        main_script: Path | str | None = None,
        shortcut_path: Path | str | None = None,
    ) -> None:
        self.main_script = (
            Path(main_script) if main_script else _resolve_main_script_path()
        )
        # .venv があれば優先し、無ければ現在の Python で起動する（Issue #209）。
        self.python_executable = python_executable or resolve_python_executable(
            self.main_script.parent,
            ("Scripts/pythonw.exe", "Scripts/python.exe"),
            _fallback_pythonw_executable(),
        )
        if shortcut_path:
            self.shortcut_path: Path | None = Path(shortcut_path)
        else:
            startup = _startup_folder()
            self.shortcut_path = startup / _SHORTCUT_NAME if startup else None

    def is_enabled(self) -> bool:
        """Startup フォルダにショートカットが存在するかを返す。"""
        if sys.platform != "win32" or self.shortcut_path is None:
            return False
        return self.shortcut_path.exists()

    def enable(self) -> bool:
        """Startup フォルダにショートカットを作成して自動起動を有効化する。"""
        if sys.platform != "win32":
            return False
        if self.shortcut_path is None:
            logger.error("Startup フォルダを特定できないため自動起動を登録できません。")
            return False

        # Arguments は引用符で囲んで組み立てるため、引用符を含むパスは拒否する。
        if '"' in str(self.main_script) or '"' in str(self.python_executable):
            logger.error("引用符を含むパスでは自動起動を登録できません。")
            return False

        try:
            from win32com.client import Dispatch

            self.shortcut_path.parent.mkdir(parents=True, exist_ok=True)
            shell: Any = Dispatch("WScript.Shell")
            shortcut: Any = shell.CreateShortCut(str(self.shortcut_path))
            shortcut.TargetPath = str(self.python_executable)
            shortcut.Arguments = f'"{self.main_script}"'
            shortcut.WorkingDirectory = str(self.main_script.parent)
            shortcut.Save()

            logger.info(
                "Startup にショートカットを作成しました: %s", self.shortcut_path
            )
            _remove_legacy_entries()
            return True
        except Exception as e:
            logger.error("Startup ショートカットの作成に失敗しました: %s", e)
            return False

    def disable(self) -> bool:
        """Startup フォルダのショートカットを削除して自動起動を無効化する。"""
        if sys.platform != "win32":
            return False

        try:
            if self.shortcut_path is not None and self.shortcut_path.exists():
                self.shortcut_path.unlink()
                logger.info(
                    "Startup のショートカットを削除しました: %s", self.shortcut_path
                )
            _remove_legacy_entries()
            return True
        except Exception as e:
            logger.error("Startup ショートカットの削除に失敗しました: %s", e)
            return False
