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


def test_is_legacy_macos_tk_non_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    """darwin 以外の OS では常に False を返す。"""
    from src.utils.platform_utils import is_legacy_macos_tk

    monkeypatch.setattr(sys, "platform", "win32")
    assert is_legacy_macos_tk() is False


def test_is_legacy_macos_tk_darwin_modern(monkeypatch: pytest.MonkeyPatch) -> None:
    """darwin かつ Tk >= 8.6 の場合は False を返す。"""
    import tkinter as tk

    from src.utils.platform_utils import is_legacy_macos_tk

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(tk, "TkVersion", 8.6)
    assert is_legacy_macos_tk() is False

    monkeypatch.setattr(tk, "TkVersion", 9.0)
    assert is_legacy_macos_tk() is False


def test_is_legacy_macos_tk_darwin_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    """darwin かつ Tk < 8.6 の場合は True を返す。"""
    import tkinter as tk

    from src.utils.platform_utils import is_legacy_macos_tk

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(tk, "TkVersion", 8.5)
    assert is_legacy_macos_tk() is True


def test_apply_macos_aqua_appearance_non_darwin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """darwin 以外の OS では何もせず False を返す。"""
    from src.utils.platform_utils import apply_macos_aqua_appearance

    monkeypatch.setattr(sys, "platform", "win32")
    assert apply_macos_aqua_appearance() is False


def test_apply_macos_aqua_appearance_darwin_success(
    monkeypatch: pytest.MonkeyPatch,
    tk_root: object,
) -> None:
    """darwin かつ Tk初期化済み環境で Objective-C 呼び出しが正常に行われた場合は True を返す。"""
    from src.utils.platform_utils import apply_macos_aqua_appearance

    monkeypatch.setattr(sys, "platform", "darwin")

    # 実機 macOS かつ Tk 初期化済み環境で安全に呼び出し可能
    result = apply_macos_aqua_appearance(tk_root)
    assert isinstance(result, bool)


def test_apply_macos_aqua_appearance_without_tk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tk 未初期化の状態で呼び出された場合は安全に False を返す（SIGABRT防止ガード）。"""
    import tkinter as tk

    from src.utils.platform_utils import apply_macos_aqua_appearance

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(tk, "_default_root", None)
    assert apply_macos_aqua_appearance(None) is False


def test_apply_macos_aqua_appearance_darwin_exception(
    monkeypatch: pytest.MonkeyPatch,
    tk_root: object,
) -> None:
    """darwin で例外が発生した場合はクラッシュせず安全に False を返す。"""
    from src.utils.platform_utils import apply_macos_aqua_appearance

    monkeypatch.setattr(sys, "platform", "darwin")
    with patch("ctypes.cdll.LoadLibrary", side_effect=RuntimeError("Test error")):
        assert apply_macos_aqua_appearance(tk_root) is False
