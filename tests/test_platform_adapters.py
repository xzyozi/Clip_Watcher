"""tests/test_platform_adapters.py

OSプラットフォーム具象アダプター（Windows / Null）およびファクトリの単体テスト。
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from src.core.platform import get_platform_adapters
from src.core.platform.null import (
    NullHotkeyListener,
    NullPasteSender,
    NullProcessInspector,
    NullSingleInstanceController,
    NullSoundPlayer,
)
from src.core.platform.protocols import (
    HotkeyListener,
    PasteSender,
    ProcessInspector,
    SingleInstanceController,
    SoundPlayer,
)
from src.core.platform.windows import (
    WindowsPasteSender,
    WindowsProcessInspector,
    WindowsSingleInstanceController,
    WindowsSoundPlayer,
)


class TestNullAdapters:
    """非 Windows / ヘッドレス環境向け Null アダプターの検証。"""

    def test_null_process_inspector(self) -> None:
        inspector = NullProcessInspector()
        assert isinstance(inspector, ProcessInspector)
        assert inspector.get_active_process_name() is None

    def test_null_single_instance_controller(self) -> None:
        controller = NullSingleInstanceController()
        assert isinstance(controller, SingleInstanceController)
        assert controller.acquire() is True
        controller.release()  # 例外が発生しないこと

    def test_null_sound_player(self) -> None:
        player = NullSoundPlayer()
        assert isinstance(player, SoundPlayer)
        assert player.play_notification_beep(1000, 200) is True

    def test_null_paste_sender(self) -> None:
        sender = NullPasteSender()
        assert isinstance(sender, PasteSender)
        assert sender.are_modifiers_released() is True
        assert sender.paste_active_window() is False

    def test_null_hotkey_listener(self) -> None:
        listener = NullHotkeyListener()
        assert isinstance(listener, HotkeyListener)
        assert listener.start(1, 65) is True
        assert listener.start_many([{"modifiers": 1, "vk_code": 65}]) is True
        listener.stop()  # 例外が発生しないこと


class TestWindowsAdapters:
    """Windows 具象アダプターの検証。"""

    def test_windows_protocols_satisfied(self) -> None:
        assert isinstance(WindowsProcessInspector(), ProcessInspector)
        assert isinstance(WindowsSingleInstanceController(), SingleInstanceController)
        assert isinstance(WindowsSoundPlayer(), SoundPlayer)
        assert isinstance(WindowsPasteSender(), PasteSender)

    def test_windows_sound_player_with_winsound(self) -> None:
        player = WindowsSoundPlayer()
        mock_winsound = MagicMock()
        with patch.dict("sys.modules", {"winsound": mock_winsound}):
            result = player.play_notification_beep(800, 150)
            assert result is True
            mock_winsound.Beep.assert_called_once_with(800, 150)

    def test_windows_sound_player_without_winsound(self) -> None:
        player = WindowsSoundPlayer()
        with patch.dict("sys.modules", {"winsound": None}):
            result = player.play_notification_beep(800, 150)
            assert result is False

    def test_windows_process_inspector_exception_fallback(self) -> None:
        inspector = WindowsProcessInspector()
        with patch("ctypes.windll", create=True) as mock_windll:
            mock_windll.user32.GetForegroundWindow.side_effect = RuntimeError("Mock error")
            assert inspector.get_active_process_name() is None


class TestPlatformFactory:
    """get_platform_adapters() ファクトリの検証。"""

    def test_get_platform_adapters_non_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "darwin")
        adapters = get_platform_adapters()

        assert isinstance(adapters["process_inspector"], NullProcessInspector)
        assert isinstance(adapters["single_instance"], NullSingleInstanceController)
        assert isinstance(adapters["sound_player"], NullSoundPlayer)
        assert isinstance(adapters["paste_sender"], NullPasteSender)

    def test_get_platform_adapters_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        adapters = get_platform_adapters()

        assert isinstance(adapters["process_inspector"], WindowsProcessInspector)
        assert isinstance(adapters["single_instance"], WindowsSingleInstanceController)
        assert isinstance(adapters["sound_player"], WindowsSoundPlayer)
        assert isinstance(adapters["paste_sender"], WindowsPasteSender)
