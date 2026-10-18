"""tests/test_sound_player.py

SoundPlayer の各 OS 実装（macOS, Linux）のユニットテスト。
CI 環境（Ubuntu / Windows）でもモックを使用して完全に検証可能とする。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.platform.linux.sound_player import LinuxSoundPlayer
from src.core.platform.macos.sound_player import MacOSSoundPlayer
from src.core.platform.protocols import SoundPlayer


class TestMacOSSoundPlayer:
    def test_implements_protocol(self) -> None:
        player = MacOSSoundPlayer()
        assert isinstance(player, SoundPlayer)

    def test_returns_false_when_not_darwin(self) -> None:
        player = MacOSSoundPlayer()
        with patch("sys.platform", "linux"):
            assert player.play_notification_beep() is False

    def test_returns_false_when_sound_file_missing(self, tmp_path: Path) -> None:
        missing_path = tmp_path / "nonexistent.aiff"
        player = MacOSSoundPlayer(missing_path)
        with patch("sys.platform", "darwin"):
            assert player.play_notification_beep() is False

    def test_plays_sound_via_afplay_success(self, tmp_path: Path) -> None:
        sound_file = tmp_path / "test.aiff"
        sound_file.touch()
        player = MacOSSoundPlayer(sound_file)

        with (
            patch("sys.platform", "darwin"),
            patch("subprocess.Popen") as mock_popen,
        ):
            assert player.play_notification_beep() is True
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            assert args[0] == "/usr/bin/afplay"
            assert args[1] == str(sound_file)

    def test_handles_popen_exception(self, tmp_path: Path) -> None:
        sound_file = tmp_path / "test.aiff"
        sound_file.touch()
        player = MacOSSoundPlayer(sound_file)

        with (
            patch("sys.platform", "darwin"),
            patch("subprocess.Popen", side_effect=OSError("Exec error")),
        ):
            assert player.play_notification_beep() is False


class TestLinuxSoundPlayer:
    def test_implements_protocol(self) -> None:
        player = LinuxSoundPlayer()
        assert isinstance(player, SoundPlayer)

    def test_returns_false_when_not_linux(self) -> None:
        player = LinuxSoundPlayer()
        with patch("sys.platform", "darwin"):
            assert player.play_notification_beep() is False

    def test_plays_via_paplay_success(self, tmp_path: Path) -> None:
        sound_file = tmp_path / "bell.oga"
        sound_file.touch()
        player = LinuxSoundPlayer(sound_file)

        with (
            patch("sys.platform", "linux"),
            patch(
                "shutil.which",
                side_effect=lambda cmd: "/usr/bin/paplay" if cmd == "paplay" else None,
            ),
            patch("subprocess.Popen") as mock_popen,
        ):
            assert player.play_notification_beep() is True
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            assert args[0] == "paplay"
            assert args[1] == str(sound_file)

    def test_plays_via_canberra_success(self) -> None:
        player = LinuxSoundPlayer()

        with (
            patch("sys.platform", "linux"),
            patch(
                "shutil.which",
                side_effect=lambda cmd: (
                    "/usr/bin/canberra-gtk-play" if cmd == "canberra-gtk-play" else None
                ),
            ),
            patch("subprocess.Popen") as mock_popen,
        ):
            assert player.play_notification_beep() is True
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            assert args[0] == "canberra-gtk-play"

    def test_plays_via_terminal_bell_fallback(self) -> None:
        player = LinuxSoundPlayer()

        mock_stdout = MagicMock()
        with (
            patch("sys.platform", "linux"),
            patch("shutil.which", return_value=None),
            patch("sys.stdout", mock_stdout),
        ):
            assert player.play_notification_beep() is True
            mock_stdout.write.assert_called_once_with("\a")
            mock_stdout.flush.assert_called_once()
