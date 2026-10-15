"""tests/test_platform_adapters.py

OSプラットフォーム具象アダプター（Windows / ホットキー用 Null）の単体テスト。

PlatformServices の振る舞いは tests/test_platform_services.py を参照。
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from src.core.platform.null import NullHotkeyListener
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


class TestNullHotkeyListener:
    """ホットキー用の暫定 Null アダプターの検証（#150 で廃止予定）。"""

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

    def test_windows_sound_player_with_winsound(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        player = WindowsSoundPlayer()
        mock_winsound = MagicMock()
        with patch.dict("sys.modules", {"winsound": mock_winsound}):
            result = player.play_notification_beep(800, 150)
            assert result is True
            mock_winsound.Beep.assert_called_once_with(800, 150)

    def test_windows_sound_player_without_winsound(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        player = WindowsSoundPlayer()
        with patch.dict("sys.modules", {"winsound": None}):
            result = player.play_notification_beep(800, 150)
            assert result is False

    def test_windows_process_inspector_exception_fallback(self) -> None:
        inspector = WindowsProcessInspector()
        with patch("ctypes.windll", create=True) as mock_windll:
            mock_windll.user32.GetForegroundWindow.side_effect = RuntimeError(
                "Mock error"
            )
            assert inspector.get_active_process_name() is None
