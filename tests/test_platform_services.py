"""tests/test_platform_services.py

PlatformServices と プラットフォーム例外の振る舞いを検証する。
アダプターはコンストラクタへモックを注入し、sys.platform の差し替えは使用しない。
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from src.core.bootstrap.exceptions import ClipWatcherError
from src.core.platform.errors import (
    PlatformError,
    SingleInstanceError,
    UnsupportedFeatureError,
)
from src.core.platform.services import PlatformServices


class TestPlatformErrors:
    def test_error_hierarchy(self) -> None:
        assert issubclass(PlatformError, ClipWatcherError)
        assert issubclass(UnsupportedFeatureError, PlatformError)
        assert issubclass(SingleInstanceError, PlatformError)

    def test_unsupported_feature_error_has_feature_and_platform(self) -> None:
        error = UnsupportedFeatureError("sound_player", "darwin")

        assert error.feature == "sound_player"
        assert error.platform == "darwin"
        assert "sound_player" in str(error)
        assert "darwin" in str(error)


class TestPlatformServices:
    def test_returns_injected_adapters(self) -> None:
        inspector, sound, single, paste, clipboard = (MagicMock() for _ in range(5))
        services = PlatformServices(
            process_inspector=inspector,
            sound_player=sound,
            single_instance=single,
            paste_sender=paste,
            clipboard_reader=clipboard,
            platform_name="win32",
        )

        assert services.process_inspector() is inspector
        assert services.sound_player() is sound
        assert services.single_instance() is single
        assert services.paste_sender() is paste
        assert services.clipboard_reader() is clipboard

    @pytest.mark.parametrize(
        "feature",
        [
            "process_inspector",
            "sound_player",
            "single_instance",
            "paste_sender",
            "clipboard_reader",
        ],
    )
    def test_unsupported_adapter_raises_unsupported_feature_error(
        self, feature: str
    ) -> None:
        services = PlatformServices(platform_name="darwin")

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            getattr(services, feature)()

        assert exc_info.value.feature == feature
        assert exc_info.value.platform == "darwin"

    def test_only_missing_adapter_raises(self) -> None:
        sound = MagicMock()
        services = PlatformServices(sound_player=sound, platform_name="linux")

        assert services.sound_player() is sound
        with pytest.raises(UnsupportedFeatureError):
            services.paste_sender()


class TestForCurrentPlatform:
    def test_windows_provides_all_four_adapters(self) -> None:
        services = PlatformServices.for_current_platform("win32")

        from src.core.platform.protocols import (
            PasteSender,
            ProcessInspector,
            SingleInstanceController,
            SoundPlayer,
        )

        assert isinstance(services.process_inspector(), ProcessInspector)
        assert isinstance(services.sound_player(), SoundPlayer)
        assert isinstance(services.single_instance(), SingleInstanceController)
        assert isinstance(services.paste_sender(), PasteSender)

    def test_windows_without_pywin32_treats_clipboard_reader_as_unsupported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """pywin32 未導入の Windows は、clipboard_reader だけを非対応として扱う。"""
        monkeypatch.setitem(sys.modules, "win32clipboard", None)
        monkeypatch.setitem(sys.modules, "pywintypes", None)

        services = PlatformServices.for_current_platform("win32")

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            services.clipboard_reader()
        assert exc_info.value.feature == "clipboard_reader"
        assert services.process_inspector() is not None

    def test_darwin_provides_clipboard_reader_only(self) -> None:
        """macOS (darwin) は ClipboardReader を提供し、他機能は非対応として扱う。"""
        services = PlatformServices.for_current_platform("darwin")

        from src.core.platform.protocols import ClipboardReader

        assert isinstance(services.clipboard_reader(), ClipboardReader)

        for feature in (
            "process_inspector",
            "sound_player",
            "single_instance",
            "paste_sender",
        ):
            with pytest.raises(UnsupportedFeatureError) as exc_info:
                getattr(services, feature)()
            assert exc_info.value.feature == feature
            assert exc_info.value.platform == "darwin"

    def test_linux_provides_no_adapters(self) -> None:
        """Linux は現時点でアダプターを持たず、全機能が UnsupportedFeatureError となる。"""
        services = PlatformServices.for_current_platform("linux")

        for feature in (
            "process_inspector",
            "sound_player",
            "single_instance",
            "paste_sender",
            "clipboard_reader",
        ):
            with pytest.raises(UnsupportedFeatureError) as exc_info:
                getattr(services, feature)()
            assert exc_info.value.feature == feature
            assert exc_info.value.platform == "linux"
