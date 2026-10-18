"""tests/test_startup_controller.py

StartupController の各 OS 実装（macOS, Windows, Linux）の単体テスト。
"""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.platform.linux.startup import LinuxStartupController
from src.core.platform.macos.startup import MacOSStartupController
from src.core.platform.protocols import StartupController
from src.core.platform.windows.startup import WindowsStartupController


class TestMacOSStartupController:
    def test_implements_protocol(self, tmp_path: Path) -> None:
        controller = MacOSStartupController(tmp_path / "test.plist")
        assert isinstance(controller, StartupController)

    def test_enable_creates_valid_plist(self, tmp_path: Path) -> None:
        plist_file = tmp_path / "LaunchAgents" / "com.clipwatcher.app.plist"
        python_exe = "/usr/local/bin/python3"
        script_path = tmp_path / "clip_watcher.py"
        script_path.touch()

        controller = MacOSStartupController(
            plist_path=plist_file,
            python_executable=python_exe,
            main_script=script_path,
        )

        assert controller.is_enabled() is False
        assert controller.enable() is True
        assert controller.is_enabled() is True
        assert plist_file.exists()

        # plist の中身を検証
        with open(plist_file, "rb") as f:
            data = plistlib.load(f)

        assert data["Label"] == "com.clipwatcher.app"
        assert data["ProgramArguments"] == [python_exe, str(script_path)]
        assert data["RunAtLoad"] is True
        assert data["ProcessType"] == "Interactive"

    def test_disable_removes_plist(self, tmp_path: Path) -> None:
        plist_file = tmp_path / "com.clipwatcher.app.plist"
        plist_file.touch()

        controller = MacOSStartupController(plist_path=plist_file)
        assert controller.is_enabled() is True
        assert controller.disable() is True
        assert controller.is_enabled() is False
        assert not plist_file.exists()


class TestWindowsStartupController:
    def test_implements_protocol(self) -> None:
        controller = WindowsStartupController()
        assert isinstance(controller, StartupController)

    def test_returns_false_when_not_win32(self) -> None:
        controller = WindowsStartupController()
        with patch("sys.platform", "darwin"):
            assert controller.is_enabled() is False
            assert controller.enable() is False
            assert controller.disable() is False

    def test_enable_sets_registry_and_removes_legacy_bat(self, tmp_path: Path) -> None:
        controller = WindowsStartupController(
            python_executable="C:\\Python\\pythonw.exe",
            main_script=tmp_path / "clip_watcher.py",
        )

        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.CreateKey.return_value.__enter__.return_value = mock_key

        # レガシーバッチの模擬
        legacy_dir = (
            tmp_path
            / "AppData"
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
        )
        legacy_dir.mkdir(parents=True)
        legacy_bat = legacy_dir / "ClipWatcher.bat"
        legacy_bat.touch()

        with (
            patch("sys.platform", "win32"),
            patch.dict(sys.modules, {"winreg": mock_winreg}),
            patch.dict("os.environ", {"APPDATA": str(tmp_path / "AppData")}),
        ):
            assert controller.enable() is True
            mock_winreg.SetValueEx.assert_called_once()
            args = mock_winreg.SetValueEx.call_args[0]
            assert args[1] == "ClipWatcher"
            assert "pythonw.exe" in args[4]
            assert not legacy_bat.exists()

    def test_disable_deletes_registry_value(self) -> None:
        controller = WindowsStartupController()
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        with (
            patch("sys.platform", "win32"),
            patch.dict(sys.modules, {"winreg": mock_winreg}),
        ):
            assert controller.disable() is True
            mock_winreg.DeleteValue.assert_called_once_with(mock_key, "ClipWatcher")


class TestLinuxStartupController:
    def test_implements_protocol(self, tmp_path: Path) -> None:
        controller = LinuxStartupController(tmp_path / "test.desktop")
        assert isinstance(controller, StartupController)

    def test_enable_creates_desktop_file(self, tmp_path: Path) -> None:
        desktop_file = tmp_path / "autostart" / "clipwatcher.desktop"
        controller = LinuxStartupController(
            desktop_path=desktop_file,
            python_executable="/usr/bin/python3",
            main_script=tmp_path / "clip_watcher.py",
        )

        assert controller.is_enabled() is False
        assert controller.enable() is True
        assert controller.is_enabled() is True
        assert desktop_file.exists()

        content = desktop_file.read_text(encoding="utf-8")
        assert "[Desktop Entry]" in content
        assert "Type=Application" in content
        assert "/usr/bin/python3" in content

    def test_disable_removes_desktop_file(self, tmp_path: Path) -> None:
        desktop_file = tmp_path / "clipwatcher.desktop"
        desktop_file.touch()

        controller = LinuxStartupController(desktop_path=desktop_file)
        assert controller.is_enabled() is True
        assert controller.disable() is True
        assert controller.is_enabled() is False
        assert not desktop_file.exists()
