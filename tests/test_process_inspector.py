"""tests/test_process_inspector.py

ProcessInspector の各 OS 実装（macOS, Linux）のユニットテスト。
CI 環境（Ubuntu / Windows）でもモックを使用して完全に検証可能とする。
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.platform.linux.process_inspector import (
    LinuxProcessInspector,
    _get_active_process_via_xprop,
)
from src.core.platform.macos.process_inspector import (
    MacOSProcessInspector,
    _get_active_process_via_appkit,
    _get_active_process_via_osascript,
)
from src.core.platform.protocols import ProcessInspector


class TestMacOSProcessInspector:
    def test_implements_protocol(self) -> None:
        inspector = MacOSProcessInspector()
        assert isinstance(inspector, ProcessInspector)

    def test_returns_none_when_not_darwin(self) -> None:
        inspector = MacOSProcessInspector()
        with patch("sys.platform", "linux"):
            assert inspector.get_active_process_name() is None

    def test_get_active_process_via_appkit_success(self) -> None:
        inspector = MacOSProcessInspector()
        with (
            patch("sys.platform", "darwin"),
            patch(
                "src.core.platform.macos.process_inspector._get_active_process_via_appkit",
                return_value="Google Chrome",
            ),
        ):
            assert inspector.get_active_process_name() == "Google Chrome"

    def test_appkit_fallback_to_osascript(self) -> None:
        inspector = MacOSProcessInspector()
        with (
            patch("sys.platform", "darwin"),
            patch(
                "src.core.platform.macos.process_inspector._get_active_process_via_appkit",
                return_value=None,
            ),
            patch(
                "src.core.platform.macos.process_inspector._get_active_process_via_osascript",
                return_value="iTerm2",
            ),
        ):
            assert inspector.get_active_process_name() == "iTerm2"

    def test_both_fail_returns_none(self) -> None:
        inspector = MacOSProcessInspector()
        with (
            patch("sys.platform", "darwin"),
            patch(
                "src.core.platform.macos.process_inspector._get_active_process_via_appkit",
                return_value=None,
            ),
            patch(
                "src.core.platform.macos.process_inspector._get_active_process_via_osascript",
                return_value=None,
            ),
        ):
            assert inspector.get_active_process_name() is None

    def test_osascript_helper_success(self) -> None:
        mock_res = MagicMock(returncode=0, stdout="KeePassXC\n")
        with patch("subprocess.run", return_value=mock_res):
            assert _get_active_process_via_osascript() == "KeePassXC"

    def test_osascript_helper_nonzero_exit(self) -> None:
        mock_res = MagicMock(returncode=1, stdout="", stderr="Error")
        with patch("subprocess.run", return_value=mock_res):
            assert _get_active_process_via_osascript() is None

    def test_osascript_helper_timeout(self) -> None:
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="osascript", timeout=1.0),
        ):
            assert _get_active_process_via_osascript() is None

    def test_osascript_helper_oserror(self) -> None:
        with patch("subprocess.run", side_effect=OSError("Command not found")):
            assert _get_active_process_via_osascript() is None

    def test_appkit_helper_handles_library_not_found(self) -> None:
        with patch("ctypes.util.find_library", return_value=None):
            assert _get_active_process_via_appkit() is None


class TestLinuxProcessInspector:
    def test_implements_protocol(self) -> None:
        inspector = LinuxProcessInspector()
        assert isinstance(inspector, ProcessInspector)

    def test_returns_none_when_not_linux(self) -> None:
        inspector = LinuxProcessInspector()
        with patch("sys.platform", "darwin"):
            assert inspector.get_active_process_name() is None

    def test_xprop_pid_and_proc_comm_success(self, tmp_path: Path) -> None:
        inspector = LinuxProcessInspector()

        # 模擬 /proc/1234/comm
        proc_dir = tmp_path / "proc"
        proc_dir.mkdir()
        pid_file = proc_dir / "comm"
        pid_file.write_text("keepassxc\n", encoding="utf-8")

        def mock_subprocess_run(cmd: list[str], **kwargs: object) -> MagicMock:
            if "_NET_ACTIVE_WINDOW" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="_NET_ACTIVE_WINDOW(WINDOW): window id # 0x1a00001\n",
                )
            if "_NET_WM_PID" in cmd:
                return MagicMock(returncode=0, stdout="_NET_WM_PID(CARDINAL) = 1234\n")
            return MagicMock(returncode=1, stdout="")

        with (
            patch("sys.platform", "linux"),
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="keepassxc\n"),
        ):
            assert inspector.get_active_process_name() == "keepassxc"

    def test_xprop_fallback_to_wm_class(self) -> None:
        inspector = LinuxProcessInspector()

        def mock_subprocess_run(cmd: list[str], **kwargs: object) -> MagicMock:
            if "_NET_ACTIVE_WINDOW" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="_NET_ACTIVE_WINDOW(WINDOW): window id # 0x1a00001\n",
                )
            if "_NET_WM_PID" in cmd:
                return MagicMock(returncode=1, stdout="")
            if "WM_CLASS" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout='WM_CLASS(STRING) = "google-chrome", "Google-chrome"\n',
                )
            return MagicMock(returncode=1, stdout="")

        with (
            patch("sys.platform", "linux"),
            patch("subprocess.run", side_effect=mock_subprocess_run),
        ):
            assert inspector.get_active_process_name() == "Google-chrome"

    def test_xprop_no_active_window(self) -> None:
        inspector = LinuxProcessInspector()
        mock_res = MagicMock(
            returncode=0, stdout="_NET_ACTIVE_WINDOW(WINDOW): window id # 0x0\n"
        )
        with (
            patch("sys.platform", "linux"),
            patch("subprocess.run", return_value=mock_res),
        ):
            assert inspector.get_active_process_name() is None

    def test_xprop_command_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError("xprop not found")):
            assert _get_active_process_via_xprop() is None

    def test_xprop_timeout(self) -> None:
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="xprop", timeout=1.0),
        ):
            assert _get_active_process_via_xprop() is None
