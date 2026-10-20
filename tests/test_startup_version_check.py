from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from clip_watcher import check_python_version, ensure_python_version


@pytest.fixture(autouse=True)
def mock_subprocess_run(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """テスト実行時に実際の osascript ダイアログがポップアップしないようモックする。"""
    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)
    return mock_run


def test_check_python_version_accepts_valid_versions() -> None:
    """Python 3.10 以上のバージョンは True を返す。"""
    assert check_python_version((3, 10, 0))[0] is True
    assert check_python_version((3, 10, 12))[0] is True
    assert check_python_version((3, 11, 0))[0] is True
    assert check_python_version((3, 12, 1))[0] is True
    assert check_python_version((3, 13, 0))[0] is True


def test_check_python_version_rejects_older_versions() -> None:
    """Python 3.10 未満のバージョンは False と詳細メッセージを返す。"""
    ok, msg = check_python_version((3, 9, 6))
    assert ok is False
    assert "Python 3.10 以上が必要です" in msg
    assert "Python 3.9.6" in msg
    assert ".venv/bin/python" in msg

    ok_38, msg_38 = check_python_version((3, 8, 10))
    assert ok_38 is False
    assert "Python 3.8.10" in msg_38


def test_ensure_python_version_exits_on_unsupported_version(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """サポート外バージョンの場合、stderr にエラーを出力して sys.exit(1) する。"""
    monkeypatch.setattr(sys, "version_info", (3, 9, 6))

    with pytest.raises(SystemExit) as exc_info:
        ensure_python_version()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "Python 3.10 以上が必要です" in captured.err


def test_ensure_python_version_passes_on_supported_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """サポート対象バージョンの場合、例外なく正常に完了する。"""
    monkeypatch.setattr(sys, "version_info", (3, 10, 5))
    # 例外なく通過すること
    ensure_python_version()


def test_ensure_python_version_attempts_macos_dialog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """macOS 環境で未対応バージョンの場合、osascript によるアラート表示が試行される。"""
    monkeypatch.setattr(sys, "version_info", (3, 9, 6))
    monkeypatch.setattr(sys, "platform", "darwin")

    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    with pytest.raises(SystemExit):
        ensure_python_version()

    assert mock_run.called
    args = mock_run.call_args[0][0]
    assert args[0] == "osascript"
    assert "display alert" in args[2]
