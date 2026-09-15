"""ApplicationBuilderの初期化順序とコンポーネント登録を検証する。"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.bootstrap.application_builder import ApplicationBuilder
from src.core.bootstrap.exceptions import ConfigError


def test_with_icon_manager_creates_and_registers_icon_manager() -> None:
    """要件5.4: IconManagerを生成し、ThemeManagerへ登録する。"""
    root = MagicMock()

    with patch(
        "src.core.bootstrap.application_builder.ThemeManager"
    ) as theme_manager_class:
        theme_manager = theme_manager_class.return_value
        builder = ApplicationBuilder().with_theme_manager(root)

        result = builder.with_icon_manager("test-assets/icons")

    assert result is builder
    assert builder.icon_manager is not None
    assert builder.icon_manager._icons_dir == "test-assets/icons"
    theme_manager.set_icon_manager.assert_called_once_with(builder.icon_manager)


def test_with_icon_manager_requires_theme_manager_to_be_initialized_first() -> None:
    """要件5.4: ThemeManager未初期化なら呼出順を示すエラーにする。"""
    builder = ApplicationBuilder()

    with pytest.raises(ConfigError, match=r"with_theme_manager\(\)"):
        builder.with_icon_manager()


def test_build_passes_icon_manager_to_main_application() -> None:
    """要件5.4: Builderは初期化済みIconManagerをMainApplicationへ渡す。"""
    builder = ApplicationBuilder()
    builder.settings_manager = MagicMock()
    builder.db_manager = MagicMock()
    builder.history_service = MagicMock()
    builder.monitor = MagicMock()
    builder.plugin_manager = MagicMock()
    builder.event_dispatcher = MagicMock()
    builder.theme_manager = MagicMock()
    builder.translator = MagicMock()
    builder.app_status = MagicMock()
    builder.icon_manager = MagicMock()
    built_app = MagicMock()

    with patch(
        "src.core.app_main.MainApplication", return_value=built_app
    ) as main_application_class:
        result = builder.build(MagicMock())

    assert result is built_app
    assert (
        main_application_class.call_args.kwargs["icon_manager"] is builder.icon_manager
    )
    built_app.on_ready.assert_called_once_with()
