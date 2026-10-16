"""tests/test_clipboard_reader.py

ClipboardReader の Windows 実装と、ClipboardMonitor のフォールバック挙動を検証する。
pywin32 は fake モジュールを注入し、windows / ubuntu の CI のどちらでも動作する。
"""

from __future__ import annotations

import logging
import sys
import tkinter as tk
import types
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.clipboard.clipboard_monitor import ClipboardMonitor
from src.core.events.event_dispatcher import EventDispatcher
from src.core.platform.services import PlatformServices
from src.core.platform.windows.clipboard_reader import WindowsClipboardReader
from src.services.history_service import HistoryService

CF_TEXT = 1
CF_UNICODETEXT = 13


class _FakePyWinTypesError(Exception):
    def __init__(self, winerror: int) -> None:
        super().__init__(winerror)
        self.winerror = winerror


def _install_fake_pywin32(
    monkeypatch: pytest.MonkeyPatch, formats: dict[int, Any]
) -> types.SimpleNamespace:
    clip = types.SimpleNamespace(
        CF_TEXT=CF_TEXT,
        CF_UNICODETEXT=CF_UNICODETEXT,
        OpenClipboard=MagicMock(),
        CloseClipboard=MagicMock(),
        IsClipboardFormatAvailable=lambda fmt: fmt in formats,
        GetClipboardData=lambda fmt: formats[fmt],
    )
    pywintypes = types.SimpleNamespace(error=_FakePyWinTypesError)
    monkeypatch.setitem(sys.modules, "win32clipboard", clip)
    monkeypatch.setitem(sys.modules, "pywintypes", pywintypes)
    return clip


class TestWindowsClipboardReader:
    def test_reads_unicode_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clip = _install_fake_pywin32(monkeypatch, {CF_UNICODETEXT: "こんにちは"})

        assert WindowsClipboardReader().read_text() == "こんにちは"
        clip.CloseClipboard.assert_called_once()

    def test_decodes_cf_text_bytes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_fake_pywin32(monkeypatch, {CF_TEXT: "テスト".encode("cp932")})

        assert WindowsClipboardReader().read_text() == "テスト"

    def test_returns_empty_string_for_unsupported_format(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_fake_pywin32(monkeypatch, {})

        assert WindowsClipboardReader().read_text() == ""

    def test_returns_none_when_clipboard_is_locked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        clip = _install_fake_pywin32(monkeypatch, {})
        clip.OpenClipboard.side_effect = _FakePyWinTypesError(5)

        assert WindowsClipboardReader().read_text() is None
        clip.CloseClipboard.assert_called_once()

    def test_returns_none_on_unexpected_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        clip = _install_fake_pywin32(monkeypatch, {})
        clip.OpenClipboard.side_effect = RuntimeError("boom")

        assert WindowsClipboardReader().read_text() is None

    def test_raises_import_error_without_pywin32(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "win32clipboard", None)
        monkeypatch.setitem(sys.modules, "pywintypes", None)

        with pytest.raises(ImportError):
            WindowsClipboardReader()


def _monitor(
    mocker: Any,
    event_dispatcher: EventDispatcher,
    history_service: HistoryService,
    services: PlatformServices,
    tk_root: Any,
) -> ClipboardMonitor:
    return ClipboardMonitor(
        tk_root=tk_root,
        event_dispatcher=event_dispatcher,
        history_file_path="dummy.json",
        db_manager=mocker.Mock(),
        history_service=history_service,
        platform_services=services,
    )


def _failing_tk_root() -> MagicMock:
    tk_root = MagicMock()
    tk_root.clipboard_get.side_effect = tk.TclError("CLIPBOARD selection doesn't exist")
    return tk_root


class TestClipboardMonitorFallback:
    def test_prefers_tkinter_over_reader(
        self,
        mocker: Any,
        event_dispatcher: EventDispatcher,
        history_service: HistoryService,
    ) -> None:
        reader = MagicMock()
        tk_root = MagicMock()
        tk_root.clipboard_get.return_value = "from tk"
        services = PlatformServices(clipboard_reader=reader, platform_name="win32")
        monitor = _monitor(mocker, event_dispatcher, history_service, services, tk_root)

        assert monitor._get_clipboard_content() == "from tk"
        reader.read_text.assert_not_called()

    def test_falls_back_to_reader_when_tkinter_fails(
        self,
        mocker: Any,
        event_dispatcher: EventDispatcher,
        history_service: HistoryService,
    ) -> None:
        reader = MagicMock()
        reader.read_text.return_value = "from reader"
        services = PlatformServices(clipboard_reader=reader, platform_name="win32")
        monitor = _monitor(
            mocker, event_dispatcher, history_service, services, _failing_tk_root()
        )

        assert monitor._get_clipboard_content() == "from reader"

    def test_returns_none_and_warns_once_when_reader_is_unsupported(
        self,
        mocker: Any,
        event_dispatcher: EventDispatcher,
        history_service: HistoryService,
        platform_services: PlatformServices,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monitor = _monitor(
            mocker,
            event_dispatcher,
            history_service,
            platform_services,
            _failing_tk_root(),
        )

        with caplog.at_level(logging.WARNING):
            assert monitor._get_clipboard_content() is None
            assert monitor._get_clipboard_content() is None

        records = [r for r in caplog.records if "clipboard_reader" in r.getMessage()]
        assert len(records) == 1

    def test_monitor_does_not_import_win32_modules(self) -> None:
        import src.core.clipboard.clipboard_monitor as module

        assert not hasattr(module, "win32clipboard")
        assert not hasattr(module, "pywintypes")
