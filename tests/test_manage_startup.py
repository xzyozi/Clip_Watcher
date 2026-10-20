"""MainApplication._manage_startup の失敗通知を検証する（Issue #205）。"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.core.app_main import MainApplication
from src.core.platform.errors import UnsupportedFeatureError


def make_app(controller: Any = None, error: Exception | None = None) -> MagicMock:
    app = MagicMock()
    if error is not None:
        app.platform_services.startup_controller.side_effect = error
    else:
        app.platform_services.startup_controller.return_value = controller
    return app


@pytest.mark.parametrize("startup_enabled", [True, False])
def test_manage_startup_shows_error_when_controller_reports_failure(
    startup_enabled: bool,
) -> None:
    """enable()/disable() が False を返したらエラーを通知する。"""
    controller = MagicMock()
    controller.enable.return_value = False
    controller.disable.return_value = False
    app = make_app(controller)

    MainApplication._manage_startup(app, startup_enabled)

    app.show_error_message.assert_called_once()
    assert app.show_error_message.call_args.args[0] == "Startup Error"


@pytest.mark.parametrize("startup_enabled", [True, False])
def test_manage_startup_is_silent_when_controller_succeeds(
    startup_enabled: bool,
) -> None:
    """成功時はエラーを通知しない。"""
    controller = MagicMock()
    controller.enable.return_value = True
    controller.disable.return_value = True
    app = make_app(controller)

    MainApplication._manage_startup(app, startup_enabled)

    app.show_error_message.assert_not_called()


def test_manage_startup_ignores_unsupported_platform() -> None:
    """非対応プラットフォームではエラーを通知しない。"""
    app = make_app(error=UnsupportedFeatureError("startup_controller", "test"))

    MainApplication._manage_startup(app, True)

    app.show_error_message.assert_not_called()
