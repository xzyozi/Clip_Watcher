"""tests/test_platform_services.py

PlatformServices と プラットフォーム例外の振る舞いを検証する。
アダプターはコンストラクタへモックを注入し、sys.platform の差し替えは使用しない。
"""

from __future__ import annotations

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
        inspector, sound, single, paste = (MagicMock() for _ in range(4))
        services = PlatformServices(
            process_inspector=inspector,
            sound_player=sound,
            single_instance=single,
            paste_sender=paste,
            platform_name="win32",
        )

        assert services.process_inspector() is inspector
        assert services.sound_player() is sound
        assert services.single_instance() is single
        assert services.paste_sender() is paste

    @pytest.mark.parametrize(
        "feature",
        ["process_inspector", "sound_player", "single_instance", "paste_sender"],
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

    @pytest.mark.parametrize("platform_name", ["darwin", "linux"])
    def test_non_windows_provides_no_adapters(self, platform_name: str) -> None:
        services = PlatformServices.for_current_platform(platform_name)

        for feature in (
            "process_inspector",
            "sound_player",
            "single_instance",
            "paste_sender",
        ):
            with pytest.raises(UnsupportedFeatureError):
                getattr(services, feature)()
