"""tests/unit/test_config_resolver_workspace_security.py

ConfigurationResolver が未検証の workspace_root を解決しないこと、および
ワークスペース設定からセキュリティ関連パラメータを緩められないことを検証する (#111)。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.text_workflow.config_resolver import (
    ConfigurationResolver,
    is_safe_workspace_root,
)

_LOAD = "src.core.text_workflow.config_resolver.load_json_config_file"


def _write_workspace_config(root: Path, data: dict[str, object]) -> None:
    config_dir = root / ".clipwatcher"
    config_dir.mkdir()
    (config_dir / "workflow.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize(
    "workspace_root",
    [r"\\evil-host\share", "//evil-host/share", r"\\?\C:\work", "relative/dir", ""],
)
def test_unsafe_workspace_root_is_rejected(workspace_root: str) -> None:
    assert is_safe_workspace_root(workspace_root) is False


def test_nonexistent_workspace_root_is_rejected(tmp_path: Path) -> None:
    assert is_safe_workspace_root(str(tmp_path / "missing")) is False


def test_existing_absolute_directory_is_accepted(tmp_path: Path) -> None:
    assert is_safe_workspace_root(str(tmp_path)) is True


@pytest.mark.parametrize("workspace_root", [r"\\evil-host\share", "//evil-host/share"])
def test_resolve_does_not_touch_filesystem_for_unc_path(workspace_root: str) -> None:
    resolver = ConfigurationResolver()

    with patch(_LOAD) as load, patch.object(os.path, "isfile") as isfile:
        resolved = resolver.resolve(workspace_root=workspace_root)

    load.assert_not_called()
    isfile.assert_not_called()
    assert resolved["workflow"]["defaultCategory"] == "general"


def test_unsafe_workspace_root_ignores_workspace_layer() -> None:
    """不正な workspace_root では、注入済みの workspace_config も使用しない。"""
    resolver = ConfigurationResolver(
        workspace_config={"workflow": {"defaultCategory": "injected"}}
    )

    resolved = resolver.resolve(workspace_root="relative/dir")

    assert resolved["workflow"]["defaultCategory"] == "general"


def test_workspace_can_tighten_security_limits(tmp_path: Path) -> None:
    _write_workspace_config(
        tmp_path,
        {
            "workflow": {
                "maxInputBytes": 100,
                "classifierRegexMaxPatternLength": 50,
                "classifierRegexTimeoutSeconds": 0.1,
            }
        },
    )

    resolved = ConfigurationResolver().resolve(workspace_root=str(tmp_path))

    assert resolved["workflow"]["maxInputBytes"] == 100
    assert resolved["workflow"]["classifierRegexMaxPatternLength"] == 50
    assert resolved["workflow"]["classifierRegexTimeoutSeconds"] == 0.1


def test_workspace_cannot_loosen_security_limits(tmp_path: Path) -> None:
    _write_workspace_config(
        tmp_path,
        {
            "workflow": {
                "maxInputBytes": 10**9,
                "classifierRegexMaxPatternLength": 10**6,
                "classifierRegexTimeoutSeconds": 3600,
                "defaultCategory": "workspace-scoped",
            }
        },
    )

    resolved = ConfigurationResolver().resolve(workspace_root=str(tmp_path))

    assert resolved["workflow"]["maxInputBytes"] == 1048576
    assert resolved["workflow"]["classifierRegexMaxPatternLength"] == 200
    assert resolved["workflow"]["classifierRegexTimeoutSeconds"] == 0.5
    # セキュリティ関連以外の設定は従来どおり上書きされる
    assert resolved["workflow"]["defaultCategory"] == "workspace-scoped"


@pytest.mark.parametrize("bad_value", ["0.0001", None, True, -1, 0])
def test_workspace_ignores_invalid_security_values(
    tmp_path: Path, bad_value: object
) -> None:
    _write_workspace_config(tmp_path, {"workflow": {"maxInputBytes": bad_value}})

    resolved = ConfigurationResolver().resolve(workspace_root=str(tmp_path))

    assert resolved["workflow"]["maxInputBytes"] == 1048576


def test_runtime_overrides_can_still_change_security_limits(tmp_path: Path) -> None:
    """呼び出し元（アプリ内のコード）が指定する実行時設定は信頼する。"""
    resolved = ConfigurationResolver().resolve(
        runtime_overrides={"workflow": {"maxInputBytes": 5_000_000}},
        workspace_root=str(tmp_path),
    )

    assert resolved["workflow"]["maxInputBytes"] == 5_000_000
