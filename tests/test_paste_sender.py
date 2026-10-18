"""tests/test_paste_sender.py

PasteSender の各 OS 実装（macOS, Linux）のユニットテスト。
CI 環境（Ubuntu / Windows）でもモックを使用して完全に検証可能とする。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.core.platform.linux.paste_sender import LinuxPasteSender
from src.core.platform.macos.paste_sender import MacOSPasteSender
from src.core.platform.protocols import PasteSender


class TestMacOSPasteSender:
    def test_implements_protocol(self) -> None:
        sender = MacOSPasteSender()
        assert isinstance(sender, PasteSender)
        assert sender.are_modifiers_released() is True

    def test_returns_false_when_not_darwin(self) -> None:
        sender = MacOSPasteSender()
        with patch("sys.platform", "linux"):
            assert sender.paste_active_window() is False

    def test_paste_success(self) -> None:
        sender = MacOSPasteSender()
        mock_res = MagicMock(returncode=0)

        with (
            patch("sys.platform", "darwin"),
            patch("subprocess.run", return_value=mock_res) as mock_run,
        ):
            assert sender.paste_active_window() is True
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "osascript" in args[0]
            assert "keystroke" in args[2]

    def test_paste_nonzero_exit(self) -> None:
        sender = MacOSPasteSender()
        mock_res = MagicMock(returncode=1, stderr="Not authorized")

        with (
            patch("sys.platform", "darwin"),
            patch("subprocess.run", return_value=mock_res),
        ):
            assert sender.paste_active_window() is False

    def test_paste_exception(self) -> None:
        sender = MacOSPasteSender()
        with (
            patch("sys.platform", "darwin"),
            patch("subprocess.run", side_effect=OSError("Command failed")),
        ):
            assert sender.paste_active_window() is False


class TestLinuxPasteSender:
    def test_implements_protocol(self) -> None:
        sender = LinuxPasteSender()
        assert isinstance(sender, PasteSender)
        assert sender.are_modifiers_released() is True

    def test_returns_false_when_not_linux(self) -> None:
        sender = LinuxPasteSender()
        with patch("sys.platform", "darwin"):
            assert sender.paste_active_window() is False

    def test_returns_false_when_xdotool_missing(self) -> None:
        sender = LinuxPasteSender()
        with (
            patch("sys.platform", "linux"),
            patch("shutil.which", return_value=None),
        ):
            assert sender.paste_active_window() is False

    def test_paste_success(self) -> None:
        sender = LinuxPasteSender()
        mock_res = MagicMock(returncode=0)

        with (
            patch("sys.platform", "linux"),
            patch("shutil.which", return_value="/usr/bin/xdotool"),
            patch("subprocess.run", return_value=mock_res) as mock_run,
        ):
            assert sender.paste_active_window() is True
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "xdotool"
            assert "ctrl+v" in args

    def test_paste_exception(self) -> None:
        sender = LinuxPasteSender()
        with (
            patch("sys.platform", "linux"),
            patch("shutil.which", return_value="/usr/bin/xdotool"),
            patch("subprocess.run", side_effect=OSError("Exec error")),
        ):
            assert sender.paste_active_window() is False
