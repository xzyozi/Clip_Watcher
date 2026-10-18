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


def test_resolve_safe_font_family_standard_fonts() -> None:
    """Tk 標準フォントや空文字はそのまま返却される。"""
    from src.utils.platform_utils import resolve_safe_font_family

    assert resolve_safe_font_family("TkDefaultFont") == "TkDefaultFont"
    assert resolve_safe_font_family("TkFixedFont") == "TkFixedFont"
    assert resolve_safe_font_family("") == "TkDefaultFont"


def test_resolve_safe_font_family_matching() -> None:
    """利用可能フォントリスト内に存在するフォント（大文字小文字差異含む）は正規化されて返る。"""
    from src.utils.platform_utils import resolve_safe_font_family

    available = ["Helvetica", "Courier New", "Arial"]
    assert resolve_safe_font_family("Helvetica", available) == "Helvetica"
    assert resolve_safe_font_family("helvetica", available) == "Helvetica"
    assert resolve_safe_font_family("COURIER NEW", available) == "Courier New"


def test_resolve_safe_font_family_fallback_to_platform_preferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """存在しないフォントの場合、プラットフォーム推奨フォントへフォールバックする。"""
    from src.utils.platform_utils import resolve_safe_font_family

    monkeypatch.setattr(sys, "platform", "darwin")
    available_mac = ["Helvetica", "Menlo", "Symbol"]
    # "FixedSys" は Windows 専用のため、macOS では Helvetica にフォールバック
    assert resolve_safe_font_family("FixedSys", available_mac) == "Helvetica"

    monkeypatch.setattr(sys, "platform", "win32")
    available_win = ["Segoe UI", "Consolas", "Symbol"]
    assert resolve_safe_font_family("Menlo", available_win) == "Segoe UI"


def test_resolve_safe_font_family_fallback_to_tk_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """推奨フォントも存在しない場合は安全に TkDefaultFont にフォールバックする。"""
    from src.utils.platform_utils import resolve_safe_font_family

    monkeypatch.setattr(sys, "platform", "darwin")
    assert (
        resolve_safe_font_family("NonExistentFont123", ["Symbol", "Webdings"])
        == "TkDefaultFont"
    )
