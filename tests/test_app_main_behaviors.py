"""MainApplication のホットキー・状態遷移・設定反映・ウィンドウ生成のテスト。

GUI・メニュー・イベントハンドラ登録・各種サービスはモックに置き換え、
アプリケーション層の振る舞いだけを検証する。
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.app_main import MainApplication
from src.core.bootstrap.base_application import ApplicationState
from src.core.hotkey.global_hotkey_listener import GLOBAL_HOTKEY_ID
from src.core.platform.errors import UnsupportedFeatureError
from src.core.platform.services import PlatformServices

# 正規化後も同じ文字列になる有効なホットキー
COMBO = "Ctrl+Shift+A"


@pytest.fixture
def parts() -> Iterator[SimpleNamespace]:
    """MainApplication と、その依存モックをまとめて返す。"""
    settings = MagicMock()
    store: dict[str, Any] = {}
    settings.get_setting.side_effect = lambda key, default=None: store.get(key, default)
    settings.set_setting.side_effect = lambda key, value: store.__setitem__(key, value)
    history = MagicMock()
    history.get_history.return_value = [
        ("pinned text", True, 5.0),
        ("plain text", False, 6.0),
    ]
    history.last_clipboard_data = "pinned text"
    hotkeys = MagicMock()
    hotkeys.reconfigure.return_value = True
    hotkeys.reconfigure_all.return_value = True
    window_state = MagicMock()
    with (
        patch("src.core.app_main.ClipWatcherGUI") as gui_cls,
        patch("src.core.app_main.menu_bar") as menu_bar,
        patch("src.event_handlers.register_class_based_handlers"),
    ):
        app = MainApplication(
            master=MagicMock(),
            settings_manager=settings,
            db_manager=MagicMock(),
            history_service=history,
            monitor=MagicMock(),
            plugin_manager=MagicMock(),
            event_dispatcher=MagicMock(),
            theme_manager=MagicMock(),
            translator=lambda key: key,
            app_status=MagicMock(),
            platform_services=PlatformServices(platform_name="test"),
            notification_manager=MagicMock(),
            window_state_manager=window_state,
            hotkey_registration_manager=hotkeys,
            text_workflow_service=MagicMock(),
        )
        yield SimpleNamespace(
            app=app,
            store=store,
            settings=settings,
            history=history,
            hotkeys=hotkeys,
            window_state=window_state,
            gui_cls=gui_cls,
            menu_bar=menu_bar,
        )


def _app(parts: SimpleNamespace) -> MainApplication:
    app: MainApplication = parts.app
    app.show_error_message = MagicMock()  # type: ignore[method-assign]
    return app


# --- 初期化・起動・終了 ---


def test_init_wires_gui_menu_and_event_subscriptions(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    parts.gui_cls.assert_called_once()
    parts.menu_bar.MenuBar.assert_called_once()
    app.monitor.sync_initial_clipboard.assert_called_once()
    app.monitor.set_error_callback.assert_called_once()
    subscribed = {c.args[0] for c in app.event_dispatcher.subscribe.call_args_list}
    assert {
        "SETTINGS_CHANGED",
        "HISTORY_UPDATED",
        "HISTORY_TOGGLE_SORT",
        "LANGUAGE_CHANGED",
        "GLOBAL_HOTKEY_TRIGGERED",
    } <= subscribed


def test_on_ready_starts_monitor_and_registers_hotkeys(parts: SimpleNamespace) -> None:
    app = _app(parts)
    app.on_ready()
    app.monitor.start.assert_called_once()
    parts.hotkeys.reconfigure.assert_called()
    app.show_error_message.assert_not_called()  # type: ignore[attr-defined]
    assert app.state == ApplicationState.RUNNING


def test_on_ready_warns_when_hotkey_registration_fails(parts: SimpleNamespace) -> None:
    app = _app(parts)
    parts.hotkeys.reconfigure.return_value = False
    app.on_ready()
    app.show_error_message.assert_called_once()  # type: ignore[attr-defined]
    app.monitor.start.assert_called_once()


def test_shutdown_stops_every_service(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    app.shutdown()
    parts.hotkeys.stop.assert_called_once()
    app.text_workflow_service.shutdown.assert_called_once()  # type: ignore[union-attr]
    app.monitor.stop.assert_called_once()
    app.monitor.save_history_to_file.assert_called_once()


def test_on_closing_shuts_down_and_destroys_window(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    app.on_closing()
    app.master.destroy.assert_called_once()
    assert app.state == ApplicationState.CLOSED


def test_stop_monitor_delegates_to_monitor(parts: SimpleNamespace) -> None:
    parts.app.stop_monitor()
    parts.app.monitor.stop.assert_called_once()


# --- ピン留めホットキー ---


def test_bindings_only_include_pinned_history_items(parts: SimpleNamespace) -> None:
    app = _app(parts)
    parts.store["pinned_hotkey_bindings"] = {
        "5": COMBO,
        "6": "Ctrl+Shift+B",  # ピン留めされていない項目は除外
        "bad": COMBO,
    }
    assert app.get_pinned_hotkey_bindings() == {5: COMBO}
    assert app.get_pinned_hotkey_combo(5) == COMBO
    assert app.get_pinned_hotkey_combo(6) is None


def test_configure_hotkey_for_pinned_item_saves_and_refreshes(
    parts: SimpleNamespace,
) -> None:
    app = _app(parts)
    assert app.configure_pinned_hotkey(5, COMBO) is True
    assert parts.store["pinned_hotkey_bindings"] == {"5": COMBO}
    parts.settings.save_settings.assert_called_once()
    parts.app.gui.update_clipboard_display.assert_called()


def test_configure_hotkey_rejects_unpinned_item(parts: SimpleNamespace) -> None:
    app = _app(parts)
    assert app.configure_pinned_hotkey(6, COMBO) is False
    app.show_error_message.assert_called_once()  # type: ignore[attr-defined]
    parts.settings.save_settings.assert_not_called()


def test_configure_hotkey_reports_registration_failure(parts: SimpleNamespace) -> None:
    app = _app(parts)
    parts.hotkeys.reconfigure_all.return_value = False
    assert app.configure_pinned_hotkey(5, COMBO) is False
    app.show_error_message.assert_called_once()  # type: ignore[attr-defined]
    parts.settings.save_settings.assert_not_called()


def test_apply_bindings_without_manager_fails(parts: SimpleNamespace) -> None:
    app = _app(parts)
    app.hotkey_registration_manager = None
    assert app.configure_pinned_hotkey(5, COMBO) is False
    assert app.clear_pinned_hotkey_bindings() is False


def test_remove_binding_variants(parts: SimpleNamespace) -> None:
    app = _app(parts)
    assert app.remove_pinned_hotkey_binding(5) is True  # 割当なしは何もせず成功

    parts.store["pinned_hotkey_bindings"] = {"5": COMBO}
    assert app.remove_pinned_hotkey_binding(5) is True
    assert parts.store["pinned_hotkey_bindings"] == {}

    parts.store["pinned_hotkey_bindings"] = {"5": COMBO}
    parts.hotkeys.reconfigure.return_value = False
    assert app.remove_pinned_hotkey_binding(5) is False
    assert parts.store["pinned_hotkey_bindings"] == {"5": COMBO}


def test_clear_bindings_success_and_failure(parts: SimpleNamespace) -> None:
    app = _app(parts)
    parts.store["pinned_hotkey_bindings"] = {"5": COMBO}
    assert app.clear_pinned_hotkey_bindings() is True
    assert parts.store["pinned_hotkey_bindings"] == {}

    parts.hotkeys.reconfigure.return_value = False
    assert app.clear_pinned_hotkey_bindings() is False


def test_open_hotkey_dialog_passes_current_combo_and_saver(
    parts: SimpleNamespace,
) -> None:
    app = _app(parts)
    parts.store["pinned_hotkey_bindings"] = {"5": COMBO}
    with patch("src.gui.dialogs.pinned_hotkey_dialog.PinnedHotkeyDialog") as dialog:
        app.open_pinned_hotkey_dialog(5)
    _, combo, on_save = dialog.call_args.args
    assert combo == COMBO
    assert on_save("Ctrl+Shift+C") is True
    assert parts.store["pinned_hotkey_bindings"]["5"] == "Ctrl+Shift+C"


# --- ホットキー発火 ---


def test_global_hotkey_toggles_window(parts: SimpleNamespace) -> None:
    app = _app(parts)
    app._on_hotkey_triggered(GLOBAL_HOTKEY_ID)
    parts.window_state.toggle.assert_called_once()


def test_global_hotkey_without_window_manager_is_ignored(
    parts: SimpleNamespace,
) -> None:
    app = _app(parts)
    app.window_state_manager = None
    app._on_hotkey_triggered(GLOBAL_HOTKEY_ID)  # 例外を送出しない


def test_pinned_hotkey_copies_item_and_schedules_paste(parts: SimpleNamespace) -> None:
    app = _app(parts)
    parts.hotkeys.history_id_for_hotkey.return_value = 5
    app._on_hotkey_triggered(GLOBAL_HOTKEY_ID + 1)
    app.master.clipboard_clear.assert_called_once()
    app.master.clipboard_append.assert_called_once_with("pinned text")
    app.notification_manager.play_notification_sound.assert_called_once()
    app.master.after.assert_called_once()


def test_pinned_hotkey_ignored_without_manager_or_binding(
    parts: SimpleNamespace,
) -> None:
    app = _app(parts)
    app.hotkey_registration_manager = None
    app._on_hotkey_triggered(GLOBAL_HOTKEY_ID + 1)
    app.master.clipboard_append.assert_not_called()

    app.hotkey_registration_manager = parts.hotkeys
    parts.hotkeys.history_id_for_hotkey.return_value = None
    app._on_hotkey_triggered(GLOBAL_HOTKEY_ID + 1)
    app.master.clipboard_append.assert_not_called()


def test_pinned_hotkey_for_missing_item_removes_stale_binding(
    parts: SimpleNamespace,
) -> None:
    app = _app(parts)
    parts.hotkeys.history_id_for_hotkey.return_value = 99
    with patch.object(app, "remove_pinned_hotkey_binding") as remove:
        app._on_hotkey_triggered(GLOBAL_HOTKEY_ID + 1)
    remove.assert_called_once_with(99)
    app.master.clipboard_append.assert_not_called()


def test_paste_gives_up_after_modifier_timeout_and_reports_failure(
    parts: SimpleNamespace,
) -> None:
    sender = MagicMock()
    sender.are_modifiers_released.return_value = False
    app = _app(parts)
    app.platform_services = PlatformServices(paste_sender=sender, platform_name="t")
    app._paste_into_active_window(waited_ms=500)
    app.master.after.assert_not_called()
    sender.paste_active_window.assert_not_called()

    sender.are_modifiers_released.return_value = True
    sender.paste_active_window.return_value = False
    app._paste_into_active_window()  # 貼り付け失敗は警告のみ
    sender.paste_active_window.assert_called_once()


def test_paste_ignores_unsupported_platform(parts: SimpleNamespace) -> None:
    app = _app(parts)
    services = MagicMock()
    services.paste_sender.side_effect = UnsupportedFeatureError("paste", "test")
    app.platform_services = services
    app._paste_into_active_window()  # 例外を送出しない


# --- 表示・メニュー ---


def test_update_gui_passes_sort_order(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    app.history_sort_ascending = True
    app.update_gui("now", [("a", False, 1.0)])
    app.gui.update_clipboard_display.assert_called_with(
        "now", [("a", False, 1.0)], True
    )


def test_history_updated_event_refreshes_gui(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    app._on_history_updated_event({"last_content": "x", "history": []})
    app.gui.update_clipboard_display.assert_called_with("x", [], False)
    app._on_history_updated_event({})
    app.gui.update_clipboard_display.assert_called_with("", [], False)


def test_toggle_sort_flips_order_and_updates_button(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    app.on_toggle_history_sort()
    assert app.history_sort_ascending is True
    app.gui.sort_button.config.assert_called_with(text="sort_asc_button")
    app.on_toggle_history_sort()
    assert app.history_sort_ascending is False
    app.gui.sort_button.config.assert_called_with(text="sort_desc_button")


def test_rebuild_menu_replaces_existing_menubar(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    old_menubar = app.menubar
    app._rebuild_menu()
    old_menubar.destroy.assert_called_once()
    app.master.config.assert_called_with(menu=app.menubar)
    app.theme_manager.set_menubar.assert_called_with(app.menubar)


def test_topmost_is_reasserted_only_when_enabled(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    app.on_focus_in()
    app.master.attributes.assert_not_called()

    parts.store["always_on_top"] = True
    app.on_focus_in()
    assert [c.args for c in app.master.attributes.call_args_list] == [
        ("-topmost", False),
        ("-topmost", True),
    ]


# --- 設定の反映 ---


def _prepare_theme(app: MainApplication, theme: str = "dark") -> None:
    app.theme_manager.get_current_theme.return_value = theme


def test_settings_change_applies_theme_topmost_and_hotkey(
    parts: SimpleNamespace,
) -> None:
    app = _app(parts)
    _prepare_theme(app)
    with patch.object(app, "_manage_startup") as startup:
        app.on_settings_changed(
            {
                "theme": "dark",
                "always_on_top": True,
                "startup_on_boot": True,
                "global_hotkey_enabled": True,
                "global_hotkey_combo": COMBO,
            }
        )
    app.theme_manager.apply_theme.assert_called_once_with("dark")
    app.gui.history_component.apply_theme.assert_called_once()
    app.master.attributes.assert_called_with("-topmost", True)
    app.main_menu.sync_settings.assert_called_once_with("dark", True)  # type: ignore[union-attr]
    startup.assert_called_once_with(True)
    parts.hotkeys.reconfigure.assert_called_once_with(True, COMBO)
    app.show_error_message.assert_not_called()  # type: ignore[attr-defined]


def test_settings_change_falls_back_to_light_for_unknown_theme(
    parts: SimpleNamespace,
) -> None:
    app = _app(parts)
    _prepare_theme(app, "light")
    with patch.object(app, "_manage_startup"):
        app.on_settings_changed({"theme": "unknown-theme"})
    app.theme_manager.apply_theme.assert_called_once_with("light")


def test_settings_change_reports_hotkey_failure(parts: SimpleNamespace) -> None:
    app = _app(parts)
    _prepare_theme(app, "light")
    parts.hotkeys.reconfigure.return_value = False
    with patch.object(app, "_manage_startup"):
        app.on_settings_changed({"global_hotkey_combo": "Ctrl+Shift+Q"})
    app.show_error_message.assert_called_once()  # type: ignore[attr-defined]


def test_settings_change_without_hotkey_manager_or_menu(
    parts: SimpleNamespace,
) -> None:
    app = _app(parts)
    _prepare_theme(app, "light")
    app.hotkey_registration_manager = None
    app.main_menu = None
    with patch.object(app, "_manage_startup"):
        app.on_settings_changed({})  # 例外を送出しない


@pytest.mark.parametrize(
    ("enable", "result", "error_expected"),
    [
        (True, True, False),
        (False, True, False),
        (True, False, True),
        (False, False, True),
    ],
)
def test_manage_startup_uses_controller(
    parts: SimpleNamespace, enable: bool, result: bool, error_expected: bool
) -> None:
    app = _app(parts)
    controller = MagicMock()
    controller.enable.return_value = result
    controller.disable.return_value = result
    app.platform_services = PlatformServices(
        startup_controller=controller, platform_name="t"
    )
    app._manage_startup(enable)
    assert (controller.enable if enable else controller.disable).called
    assert app.show_error_message.called is error_expected  # type: ignore[attr-defined]


def test_manage_startup_handles_unsupported_and_unexpected_errors(
    parts: SimpleNamespace,
) -> None:
    app = _app(parts)
    services = MagicMock()
    services.startup_controller.side_effect = UnsupportedFeatureError("startup", "test")
    app.platform_services = services
    app._manage_startup(True)
    app.show_error_message.assert_not_called()  # type: ignore[attr-defined]

    services.startup_controller.side_effect = RuntimeError("boom")
    app._manage_startup(True)
    app.show_error_message.assert_called_once()  # type: ignore[attr-defined]


# --- ウィンドウ生成 ---


def test_create_toplevel_applies_topmost_and_transient(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    parts.store["always_on_top"] = True
    window = MagicMock()
    window.winfo_exists.return_value = True
    window_cls = MagicMock(return_value=window)

    result = app.create_toplevel(window_cls, "extra", key="value")  # type: ignore[arg-type]

    window_cls.assert_called_once_with(app.master, app, "extra", key="value")
    window.attributes.assert_called_once_with("-topmost", True)
    window.transient.assert_called_once_with(app.master)
    assert result is window


def test_create_toplevel_skips_configuration_for_closed_window(
    parts: SimpleNamespace,
) -> None:
    app: MainApplication = parts.app
    window = MagicMock()
    window.winfo_exists.return_value = False
    app.create_toplevel(MagicMock(return_value=window))  # type: ignore[arg-type]
    window.transient.assert_not_called()


def test_open_settings_window_creates_settings_toplevel(
    parts: SimpleNamespace,
) -> None:
    app: MainApplication = parts.app
    with patch.object(app, "create_toplevel") as create:
        app.open_settings_window()
    create.assert_called_once()
    assert create.call_args.args[1] is app.settings_manager


def test_show_error_message_uses_message_box(parts: SimpleNamespace) -> None:
    app: MainApplication = parts.app
    with patch("src.core.app_main.messagebox.showerror") as show:
        app.show_error_message("Title", "Message")
    show.assert_called_once_with("Title", "Message")
