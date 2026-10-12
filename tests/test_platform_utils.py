"""tests/test_platform_utils.py

OS プラットフォームユーティリティの単体テスト。
"""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.utils.platform_utils import is_macos_dark_mode


def test_is_macos_dark_mode_non_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    """darwin 以外の OS では常に False を返す。"""
    monkeypatch.setattr(sys, "platform", "win32")
    assert is_macos_dark_mode() is False

    monkeypatch.setattr(sys, "platform", "linux")
    assert is_macos_dark_mode() is False


def test_is_macos_dark_mode_darwin_dark(monkeypatch: pytest.MonkeyPatch) -> None:
    """macOS で defaults コマンドが 'Dark' を返した場合は True を返す。"""
    monkeypatch.setattr(sys, "platform", "darwin")
    mock_res = MagicMock(stdout="Dark\n")
    with patch("subprocess.run", return_value=mock_res):
        assert is_macos_dark_mode() is True


def test_is_macos_dark_mode_darwin_light(monkeypatch: pytest.MonkeyPatch) -> None:
    """macOS で defaults コマンドが空または別文字列を返した場合は False を返す。"""
    monkeypatch.setattr(sys, "platform", "darwin")
    mock_res = MagicMock(stdout="")
    with patch("subprocess.run", return_value=mock_res):
        assert is_macos_dark_mode() is False


def test_is_macos_dark_mode_exception_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """subprocess.run が例外を送出した場合は安全に False を返す。"""
    monkeypatch.setattr(sys, "platform", "darwin")
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("Failed")):
        assert is_macos_dark_mode() is False
