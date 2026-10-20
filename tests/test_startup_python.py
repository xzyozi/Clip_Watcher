"""自動起動で使う Python 実行ファイル選択の共通処理を検証する（Issue #209）。"""

from __future__ import annotations

import sys
from pathlib import Path

from src.core.platform.linux.startup import LinuxStartupController
from src.core.platform.macos.startup import MacOSStartupController
from src.core.platform.startup_python import resolve_python_executable


def test_prefers_dot_venv_over_fallback(tmp_path: Path) -> None:
    python = tmp_path / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()

    assert resolve_python_executable(tmp_path, ("bin/python",), "/fb") == str(python)


def test_uses_venv_dir_when_dot_venv_is_missing(tmp_path: Path) -> None:
    python = tmp_path / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()

    assert resolve_python_executable(tmp_path, ("bin/python",), "/fb") == str(python)


def test_falls_back_when_no_venv_exists(tmp_path: Path) -> None:
    assert resolve_python_executable(tmp_path, ("bin/python",), "/fb") == "/fb"


def test_ignores_venv_directory_without_executable(tmp_path: Path) -> None:
    (tmp_path / ".venv" / "bin").mkdir(parents=True)

    assert resolve_python_executable(tmp_path, ("bin/python",), "/fb") == "/fb"


def test_macos_without_venv_falls_back_to_current_python(tmp_path: Path) -> None:
    controller = MacOSStartupController(
        plist_path=tmp_path / "a.plist", main_script=tmp_path / "clip_watcher.py"
    )

    assert controller.python_executable == sys.executable


def test_macos_prefers_venv_python(tmp_path: Path) -> None:
    python = tmp_path / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()

    controller = MacOSStartupController(
        plist_path=tmp_path / "a.plist", main_script=tmp_path / "clip_watcher.py"
    )

    assert controller.python_executable == str(python)


def test_linux_without_venv_falls_back_to_current_python(tmp_path: Path) -> None:
    controller = LinuxStartupController(
        desktop_path=tmp_path / "a.desktop", main_script=tmp_path / "clip_watcher.py"
    )

    assert controller.python_executable == sys.executable
