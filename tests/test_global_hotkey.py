"""tests/test_global_hotkey.py

GlobalHotkeyListener / parse_hotkey_string / format_hotkey / HotkeyRegistrationManager の単体テスト。
"""

from unittest.mock import MagicMock

import pytest

from src.core.hotkey.global_hotkey_listener import (
    MOD_ALT,
    MOD_CONTROL,
    MOD_SHIFT,
    format_hotkey,
    parse_hotkey_string,
)
from src.core.hotkey.hotkey_registration_manager import HotkeyRegistrationManager


def test_parse_hotkey_string_valid() -> None:
    mods, vk = parse_hotkey_string("Ctrl+Shift+F")
    assert mods == (MOD_CONTROL | MOD_SHIFT)
    assert vk == ord("F")

    mods2, vk2 = parse_hotkey_string("Alt+Control+Shift+K")
    assert mods2 == (MOD_ALT | MOD_CONTROL | MOD_SHIFT)
    assert vk2 == ord("K")


def test_parse_hotkey_string_invalid() -> None:
    with pytest.raises(ValueError):
        parse_hotkey_string("F")

    with pytest.raises(ValueError):
        parse_hotkey_string("Ctrl+InvalidKey+F")

    with pytest.raises(ValueError):
        parse_hotkey_string("Ctrl+Shift+12")


def test_format_hotkey() -> None:
    formatted = format_hotkey(MOD_CONTROL | MOD_SHIFT, ord("F"))
    assert formatted == "Ctrl+Shift+F"


def test_hotkey_registration_manager_reconfigure_same() -> None:
    mock_listener = MagicMock()
    manager = HotkeyRegistrationManager(mock_listener)

    assert manager.reconfigure(False, "") is True
    mock_listener.start.assert_not_called()


def test_hotkey_registration_manager_disable() -> None:
    mock_listener = MagicMock()
    manager = HotkeyRegistrationManager(mock_listener)

    # 最初に有効化
    mock_listener.start.return_value = True
    assert manager.reconfigure(True, "Ctrl+Shift+F") is True
    assert manager.current_enabled is True

    # 無効化
    assert manager.reconfigure(False, "Ctrl+Shift+F") is True
    assert manager.current_enabled is False
    mock_listener.stop.assert_called()


def test_hotkey_registration_manager_conflict_fallback() -> None:
    mock_listener = MagicMock()
    manager = HotkeyRegistrationManager(mock_listener)

    # 1. 最初キー A を正常登録
    mock_listener.start.return_value = True
    assert manager.reconfigure(True, "Ctrl+Shift+A") is True
    assert manager.current_combo == "Ctrl+Shift+A"

    # 2. 次にキー B に変更しようとするが競合で失敗する
    mock_listener.start.return_value = False

    # 復元でキー A は成功
    def side_effect(mods, vk):
        if vk == ord("A"):
            return True
        return False

    mock_listener.start.side_effect = side_effect

    res = manager.reconfigure(True, "Ctrl+Shift+B")
    assert res is False
    assert manager.current_enabled is True
    assert manager.current_combo == "Ctrl+Shift+A"
