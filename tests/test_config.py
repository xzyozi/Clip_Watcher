from __future__ import annotations

import os
from typing import Any

import pytest

from src.core.clipboard.clipboard_monitor import ClipboardMonitor
from src.core.config.settings_manager import SettingsManager
from src.core.events.event_dispatcher import EventDispatcher
from src.services.history_service import HistoryService

# ==========================================
# SettingsManager Tests (2 Items)
# ==========================================

@pytest.fixture
def temp_settings_file() -> Any:
    """テスト用の一時的な設定ファイルパスを提供し、テスト後にクリーンアップします。"""
    filepath = "test_temp_settings.json"
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass
    yield filepath
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass


def test_settings_manager_load_and_save(event_dispatcher: EventDispatcher, temp_settings_file: str) -> None:
    """設定ファイルのロード・セーブ、および不足キーがある場合のデフォルト復元を検証します。"""
    manager = SettingsManager(event_dispatcher=event_dispatcher, file_path=temp_settings_file)

    # 1. 初期状態 (デフォルト) の取得
    assert manager.get_setting("history_limit") > 0
    assert manager.get_setting("theme") is not None

    # 2. 値の書き換えとセーブ
    manager.set_setting("history_limit", 15)
    manager.set_setting("theme", "DarkBlue")
    manager.save_settings()

    # ファイルが正しく生成されていること
    assert os.path.exists(temp_settings_file) is True

    # 3. 再ロードによる復元
    new_manager = SettingsManager(event_dispatcher=event_dispatcher, file_path=temp_settings_file)
    new_manager.load_and_notify()
    assert new_manager.get_setting("history_limit") == 15
    assert new_manager.get_setting("theme") == "DarkBlue"


def test_settings_manager_event_trigger(event_dispatcher: EventDispatcher, temp_settings_file: str) -> None:
    """設定変更セーブおよびロード時に SETTINGS_CHANGED イベントが正しく発火することを検証します。"""
    manager = SettingsManager(event_dispatcher=event_dispatcher, file_path=temp_settings_file)

    received_settings: dict[str, Any] = {}

    def on_settings_changed(payload: dict[str, Any]) -> None:
        nonlocal received_settings
        received_settings = payload

    event_dispatcher.subscribe("SETTINGS_CHANGED", on_settings_changed)

    # 保存時の発火検証
    manager.set_setting("history_limit", 99)
    manager.save_settings()

    assert received_settings != {}
    assert received_settings.get("history_limit") == 99


# ==========================================
# ClipboardMonitor / Exclusion & Processes (2 Items)
# ==========================================

def test_clipboard_monitor_exclusion(mocker: Any, event_dispatcher: EventDispatcher, history_service: HistoryService) -> None:
    """除外プロセスが合致した場合に、クリップボードデータ更新がスキップされることを検証します。"""
    # 依存オブジェクトのモック化
    mock_tk_root = mocker.Mock()
    mock_db_manager = mocker.Mock()

    monitor = ClipboardMonitor(
        tk_root=mock_tk_root,
        event_dispatcher=event_dispatcher,
        history_file_path="dummy.json",
        win32_available=False,
        db_manager=mock_db_manager,
        history_service=history_service,
        history_limit=5,
        excluded_apps=["KeePass.exe", "PasswordManager.exe"]
    )

    # 1. 通常アプリからのコピー (履歴に追加されるべき)
    mocker.patch.object(monitor, "get_active_process_name", return_value="notepad.exe")
    monitor._update_history_with_new_entry("Sensitive Data from Notepad")

    # 履歴件数が 1 件になっていること
    assert len(history_service.history) == 1
    assert history_service.history[0][0] == "Sensitive Data from Notepad"

    # 2. 除外アプリ KeePass.exe からのコピー (履歴の更新がスキップされるべき)
    mocker.patch.object(monitor, "get_active_process_name", return_value="KeePass.exe")
    monitor._update_history_with_new_entry("Secret Password 123")

    # 履歴が追加されず、件数が 1 件のままであること
    assert len(history_service.history) == 1
    assert history_service.history[0][0] != "Secret Password 123"


def test_clipboard_monitor_update_clipboard(mocker: Any, event_dispatcher: EventDispatcher, history_service: HistoryService) -> None:
    """update_clipboard 命令時に、OSクリップボードへの書き込みと履歴登録が連動することを検証します。"""
    mock_tk_root = mocker.Mock()
    mock_db_manager = mocker.Mock()

    monitor = ClipboardMonitor(
        tk_root=mock_tk_root,
        event_dispatcher=event_dispatcher,
        history_file_path="dummy.json",
        win32_available=False,
        db_manager=mock_db_manager,
        history_service=history_service,
        history_limit=5
    )

    # アプリの履歴初期化
    history_service.clear_history()

    # コマンドでクリップボード更新を要求
    monitor.update_clipboard("Programmatic Copy Text")

    # 1. Tkinterのクリップボード書き込みメソッドが呼ばれたこと
    mock_tk_root.clipboard_clear.assert_called_once()
    mock_tk_root.clipboard_append.assert_called_once_with("Programmatic Copy Text")
    mock_tk_root.update.assert_called_once()

    # 2. 履歴サービスにも正しく登録されていること
    assert len(history_service.history) == 1
    assert history_service.history[0][0] == "Programmatic Copy Text"
