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

    @staticmethod
    def _fake_win32com(shortcut: MagicMock) -> MagicMock:
        """win32com.client.Dispatch("WScript.Shell").CreateShortCut を模擬する。"""
        client = MagicMock()
        client.Dispatch.return_value.CreateShortCut.return_value = shortcut
        return client

    def test_enable_creates_shortcut_and_never_writes_registry(
        self, tmp_path: Path
    ) -> None:
        script = tmp_path / "clip_watcher.py"
        lnk = tmp_path / "Startup" / "ClipWatcher.lnk"
        controller = WindowsStartupController(
            python_executable="C:\\Python\\pythonw.exe",
            main_script=script,
            shortcut_path=lnk,
        )
        shortcut = MagicMock()
        client = self._fake_win32com(shortcut)
        mock_winreg = MagicMock()

        with (
            patch("sys.platform", "win32"),
            patch.dict(
                sys.modules,
                {
                    "win32com": MagicMock(client=client),
                    "win32com.client": client,
                    "winreg": mock_winreg,
                },
            ),
            patch.dict("os.environ", {"APPDATA": str(tmp_path / "AppData")}),
        ):
            assert controller.enable() is True

        assert shortcut.TargetPath == "C:\\Python\\pythonw.exe"
        assert shortcut.Arguments == f'"{script}"'
        assert shortcut.WorkingDirectory == str(tmp_path)
        shortcut.Save.assert_called_once_with()
        client.Dispatch.return_value.CreateShortCut.assert_called_once_with(str(lnk))
        mock_winreg.CreateKey.assert_not_called()
        mock_winreg.SetValueEx.assert_not_called()

    def test_enable_removes_legacy_bat_and_registry_value(self, tmp_path: Path) -> None:
        startup_dir = (
            tmp_path
            / "AppData"
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
        )
        startup_dir.mkdir(parents=True)
        legacy_bat = startup_dir / "ClipWatcher.bat"
        legacy_bat.touch()
        old_dir = tmp_path / "AppData" / "Microsoft" / "Windows" / "Startup"
        old_dir.mkdir(parents=True)
        old_bat = old_dir / "ClipWatcher.bat"
        old_bat.touch()

        controller = WindowsStartupController(
            python_executable="C:\\Python\\pythonw.exe",
            main_script=tmp_path / "clip_watcher.py",
            shortcut_path=startup_dir / "ClipWatcher.lnk",
        )
        client = self._fake_win32com(MagicMock())
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        with (
            patch("sys.platform", "win32"),
            patch.dict(
                sys.modules,
                {
                    "win32com": MagicMock(client=client),
                    "win32com.client": client,
                    "winreg": mock_winreg,
                },
            ),
            patch.dict("os.environ", {"APPDATA": str(tmp_path / "AppData")}),
        ):
            assert controller.enable() is True

        assert not legacy_bat.exists()
        assert not old_bat.exists()
        mock_winreg.DeleteValue.assert_called_once_with(mock_key, "ClipWatcher")

    def test_enable_rejects_paths_containing_quotes(self, tmp_path: Path) -> None:
        controller = WindowsStartupController(
            python_executable="C:\\Python\\pythonw.exe",
            main_script=tmp_path / 'evil".py',
            shortcut_path=tmp_path / "ClipWatcher.lnk",
        )
        client = self._fake_win32com(MagicMock())

        with (
            patch("sys.platform", "win32"),
            patch.dict(
                sys.modules,
                {"win32com": MagicMock(client=client), "win32com.client": client},
            ),
        ):
            assert controller.enable() is False

        client.Dispatch.assert_not_called()

    def test_enable_returns_false_when_shortcut_creation_fails(
        self, tmp_path: Path
    ) -> None:
        controller = WindowsStartupController(
            python_executable="C:\\Python\\pythonw.exe",
            main_script=tmp_path / "clip_watcher.py",
            shortcut_path=tmp_path / "ClipWatcher.lnk",
        )
        client = MagicMock()
        client.Dispatch.side_effect = OSError("COM unavailable")

        with (
            patch("sys.platform", "win32"),
            patch.dict(
                sys.modules,
                {"win32com": MagicMock(client=client), "win32com.client": client},
            ),
        ):
            assert controller.enable() is False

    def test_is_enabled_reflects_shortcut_existence(self, tmp_path: Path) -> None:
        lnk = tmp_path / "ClipWatcher.lnk"
        controller = WindowsStartupController(shortcut_path=lnk)

        with patch("sys.platform", "win32"):
            assert controller.is_enabled() is False
            lnk.touch()
            assert controller.is_enabled() is True

    def test_disable_removes_shortcut_and_legacy_registry_value(
        self, tmp_path: Path
    ) -> None:
        lnk = tmp_path / "ClipWatcher.lnk"
        lnk.touch()
        controller = WindowsStartupController(shortcut_path=lnk)
        mock_winreg = MagicMock()
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key

        with (
            patch("sys.platform", "win32"),
            patch.dict(sys.modules, {"winreg": mock_winreg}),
            patch.dict("os.environ", {"APPDATA": str(tmp_path / "AppData")}),
        ):
            assert controller.disable() is True

        assert not lnk.exists()
        mock_winreg.DeleteValue.assert_called_once_with(mock_key, "ClipWatcher")

    def test_default_python_prefers_venv_pythonw(self, tmp_path: Path) -> None:
        pythonw = tmp_path / ".venv" / "Scripts" / "pythonw.exe"
        pythonw.parent.mkdir(parents=True)
        pythonw.touch()

        controller = WindowsStartupController(
            main_script=tmp_path / "clip_watcher.py",
            shortcut_path=tmp_path / "ClipWatcher.lnk",
        )

        assert controller.python_executable == str(pythonw)

    def test_default_python_falls_back_to_current_python(self, tmp_path: Path) -> None:
        controller = WindowsStartupController(
            main_script=tmp_path / "clip_watcher.py",
            shortcut_path=tmp_path / "ClipWatcher.lnk",
        )

        assert Path(controller.python_executable).exists()


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
