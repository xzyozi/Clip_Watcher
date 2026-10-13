"""tests/test_platform_protocols.py

OSプラットフォーム抽象インターフェース（Protocol）の整合性・ランタイム検査を検証する単体テスト。
"""

from collections.abc import Iterable
from typing import Any

from src.core.platform.protocols import (
    HotkeyListener,
    PasteSender,
    ProcessInspector,
    SingleInstanceController,
    SoundPlayer,
)
from src.core.platform.windows.paste_sender import WindowsPasteSender


class DummyProcessInspector:
    def get_active_process_name(self) -> str | None:
        return "dummy_process.exe"


class DummySingleInstanceController:
    def __init__(self) -> None:
        self.locked = False

    def acquire(self) -> bool:
        if self.locked:
            return False
        self.locked = True
        return True

    def release(self) -> None:
        self.locked = False


class DummySoundPlayer:
    def play_notification_beep(
        self, frequency: int = 1000, duration_ms: int = 200
    ) -> bool:
        return True


class DummyPasteSender:
    def are_modifiers_released(self) -> bool:
        return True

    def paste_active_window(self) -> bool:
        return True


class DummyHotkeyListener:
    def start(self, modifiers: int, vk_code: int) -> bool:
        return True

    def start_many(self, registrations: Iterable[Any]) -> bool:
        return True

    def stop(self) -> None:
        pass


def test_process_inspector_protocol() -> None:
    inspector = DummyProcessInspector()
    assert isinstance(inspector, ProcessInspector)
    assert inspector.get_active_process_name() == "dummy_process.exe"


def test_single_instance_controller_protocol() -> None:
    controller = DummySingleInstanceController()
    assert isinstance(controller, SingleInstanceController)
    assert controller.acquire() is True
    assert controller.acquire() is False
    controller.release()
    assert controller.acquire() is True


def test_sound_player_protocol() -> None:
    player = DummySoundPlayer()
    assert isinstance(player, SoundPlayer)
    assert player.play_notification_beep(1000, 200) is True


def test_paste_sender_protocol() -> None:
    sender = DummyPasteSender()
    assert isinstance(sender, PasteSender)
    assert sender.are_modifiers_released() is True
    assert sender.paste_active_window() is True


def test_windows_paste_sender_satisfies_protocol() -> None:
    windows_sender = WindowsPasteSender()
    assert isinstance(windows_sender, PasteSender)


def test_hotkey_listener_protocol() -> None:
    listener = DummyHotkeyListener()
    assert isinstance(listener, HotkeyListener)
    assert listener.start(1, 65) is True
    assert listener.start_many([]) is True
