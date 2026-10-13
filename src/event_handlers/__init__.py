from __future__ import annotations

import logging
import os
import sys
import tkinter as tk
import traceback
from tkinter import messagebox
from typing import TYPE_CHECKING, Any

from src.core.bootstrap.application_builder import ApplicationBuilder
from src.core.platform.errors import SingleInstanceError, UnsupportedFeatureError
from src.core.platform.protocols import SingleInstanceController
from src.core.platform.services import PlatformServices
from src.utils.logging_config import setup_logging

# Import standalone handlers so they can be accessed via the package
from . import main_handlers  # noqa: F401
from .file_handlers import FileEventHandlers
from .history_handlers import HistoryEventHandlers
from .settings_handlers import SettingsEventHandlers

if TYPE_CHECKING:
    from src.core.bootstrap.base_application import BaseApplication


def register_class_based_handlers(app_instance: BaseApplication) -> None:
    """
    Initializes and registers all class-based event handlers for the application.
    """
    app_instance.history_handlers = HistoryEventHandlers(
        app_instance, app_instance.event_dispatcher, app_instance.undo_manager
    )  # type: ignore
    app_instance.file_handlers = FileEventHandlers(
        app_instance, app_instance.event_dispatcher
    )  # type: ignore
    app_instance.settings_handlers = SettingsEventHandlers(
        app_instance.event_dispatcher, app_instance.settings_manager
    )  # type: ignore


def _acquire_single_instance(
    platform_services: PlatformServices,
) -> tuple[SingleInstanceController | None, bool]:
    """多重起動防止のロックを取得し、(保持するコントローラー, 重複起動か) を返す。

    - 取得成功: (controller, False)
    - 他のインスタンスが起動中: (None, True)
    - 非対応環境: (None, False)。呼び出し側で警告し、多重起動を許したまま起動する。

    Raises:
        SingleInstanceError: ロック取得 API の失敗（重複起動とは区別する）。
    """
    try:
        controller = platform_services.single_instance()
    except UnsupportedFeatureError:
        return None, False
    if not controller.acquire():
        return None, True
    return controller, False


def _release_single_instance(controller: SingleInstanceController | None) -> None:
    """保持している SingleInstanceController の排他ロックを解放する。"""
    if controller is not None:
        controller.release()


def start_app() -> None:
    platform_services = PlatformServices.for_current_platform()
    controller: SingleInstanceController | None = None
    try:
        controller, already_running = _acquire_single_instance(platform_services)
        if already_running:
            messagebox.showinfo("Already Running", "Clip Watcher is already running.")
            return

        # --- Path Definitions ---
        if sys.platform == "win32":
            app_data_dir = os.path.join(os.environ["USERPROFILE"], ".clipWatcher")
        else:
            app_data_dir = os.path.join(os.path.expanduser("~"), ".clipwatcher")
        os.makedirs(app_data_dir, exist_ok=True)

        history_file_path = os.path.join(app_data_dir, "history.json")
        settings_file_path = os.path.join(app_data_dir, "settings.json")
        db_path = os.path.join(app_data_dir, "clip_watcher.db")

        # --- Logging ---
        logger = setup_logging()
        logger.info("=== ClipWatcher アプリケーションを開始します ===")
        logger.info(
            "[DIAG] 実行環境: Python %s (%s), Platform: %s",
            sys.version.split()[0],
            sys.executable,
            sys.platform,
        )
        if sys.platform == "darwin":
            from src.utils.platform_utils import is_macos_dark_mode

            logger.info(
                "[DIAG] macOS 外観判定: is_macos_dark_mode=%s",
                is_macos_dark_mode(),
            )
        if controller is None:
            logger.warning(
                "single_instance が非対応のため、多重起動を防止できません。"
                "複数のインスタンスが同時に起動すると、履歴DBが競合する可能性があります。"
            )

        # --- Migration ---
        try:
            from scripts.migrate_json_to_sqlite import main as run_migration

            run_migration()
        except Exception as e:
            logger.error(
                "マイグレーションの実行中にエラーが発生しました: %s",
                str(e),
                exc_info=True,
            )

        # --- Application Setup ---
        # Tk 9.0 + Python < 3.13 互換性パッチ（空メニュー index が空文字を返し TclError になる問題の安全回避）
        try:

            def _compat_menu_index(self: tk.Menu, index: Any) -> int | None:
                w = getattr(self, "_w", "")
                i = self.tk.call(w, "index", index)
                if i in ("none", ""):
                    return None
                return self.tk.getint(i)

            tk.Menu.index = _compat_menu_index  # type: ignore[assignment]
        except Exception:
            pass

        root = tk.Tk()
        tk_ver = getattr(tk, "TkVersion", 0.0)
        tcl_ver = getattr(tk, "TclVersion", 0.0)
        logger.info(
            "[DIAG] Tkinter 初期化完了: TkVersion=%s, TclVersion=%s",
            tk_ver,
            tcl_ver,
        )

        if sys.platform == "darwin":
            from src.utils.platform_utils import (
                apply_macos_aqua_appearance,
                is_legacy_macos_tk,
            )

            if is_legacy_macos_tk():
                # Tk 8.5 レガシー環境向け: Cocoa の Aqua 外観を強制適用
                applied = apply_macos_aqua_appearance(root)
                logger.info(
                    "[DIAG] macOS Aqua 外観強制設定: result=%s",
                    applied,
                )
                error_msg = (
                    f"macOS システム標準の Tk {tk_ver} は、OS の描画アーキテクチャ (CoreAnimation) に"
                    "対応しておらず、ウィンドウ内容が描画されません。\n\n"
                    "本アプリケーションの動作には Tk 8.6 以上 (Python 3.10+) が必要です。"
                )
                logger.error("[ERROR-RUNTIME] %s", error_msg)

                # 白画面で放置されるのを防ぐため、ネイティブアラートで案内して安全に終了
                try:
                    import subprocess

                    subprocess.run(
                        [
                            "osascript",
                            "-e",
                            f'display alert "Clip Watcher 起動エラー" message "{error_msg}" as critical',
                        ],
                        check=False,
                        timeout=10,
                    )
                except Exception:
                    pass

                root.destroy()
                return
        if sys.version_info < (3, 10):  # noqa: UP036
            logger.warning(
                "[WARN-RUNTIME] サポート外の Python バージョン (%s) が検出されました。"
                "本アプリケーションは Python >= 3.10 を前提としています。",
                sys.version.split()[0],
            )

        builder = ApplicationBuilder(platform_services)
        app = (
            builder.with_event_dispatcher()
            .with_dependency_check()
            .with_settings(settings_file_path)
            .with_database(db_path)
            .with_translator()
            .with_theme_manager(root)
            .with_icon_manager()
            .with_history_service()
            .with_text_workflow_service(root, app_data_dir)
            .with_plugin_manager()
            .with_window_state_manager(root)
            .with_global_hotkey_listener(root)
            .with_hotkey_registration_manager()
            .with_clipboard_monitor(root, history_file_path)
            .build(root)
        )

        logger.info("アプリケーションの初期化が完了しました")

        root.mainloop()

    except SingleInstanceError as e:
        # 排他ロック取得 API の失敗。重複起動（Already Running）とは区別して通知する。
        local_logger = locals().get("logger") or logging.getLogger(__name__)
        local_logger.error("多重起動の確認に失敗しました: %s", e, exc_info=True)
        messagebox.showerror(
            "Clip Watcher",
            f"多重起動の確認に失敗したため、起動を中止しました。\n\n{e}",
        )
    except Exception as e:
        # Use a local logger variable to avoid UnboundLocalError
        local_logger = locals().get("logger")
        if local_logger:
            local_logger.error(f"アプリケーション起動エラー: {str(e)}", exc_info=True)
        else:
            print(f"アプリケーション起動エラー: {str(e)}")
        traceback.print_exc()
    finally:
        _release_single_instance(controller)
