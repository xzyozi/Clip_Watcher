from __future__ import annotations

import copy
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

WORKSPACE_CONFIG_DIR_NAME = ".clipwatcher"
WORKSPACE_CONFIG_FILE_NAME = "workflow.json"

DEFAULT_BUILTIN_CONFIG: dict[str, Any] = {
    "schemaVersion": 1,
    "workflow": {
        "defaultCategory": "general",
        "maxInputBytes": 1048576,  # 1 MB
        "defaultTemplateId": "plain",
        "normalizationProfiles": {
            "plain": ["normalize-newlines", "trim-trailing-space"],
            "issue": [
                "normalize-newlines",
                "trim-trailing-space",
                "ensure-final-newline",
            ],
        },
    },
    "history": {
        "enabled": True,
        "maxRecords": 500,
    },
    "rules": [],
    "templates": [],
}


def deep_overlay(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """
    2つの辞書を再帰的にマージする。
    辞書の値が辞書同士であれば深層マージする。
    配列やその他の型は上位 (overlay) の値で完全置換する。
    """
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_overlay(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_json_config_file(path: str) -> dict[str, Any]:
    """JSON設定ファイルを読み込む。

    ファイルが存在しない場合は空辞書を返す。JSONのパースに失敗した場合、
    または最上位要素が辞書でない場合も空辞書を返し、警告ログを出力する
    （設定破損時にアプリ起動を止めない安全な失敗方針、DD-003 §7参照）。
    """
    if not os.path.isfile(path):
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(
            "TextWorkflow設定ファイルの読み込みに失敗しました: %s (%s)", path, e
        )
        return {}

    if not isinstance(data, dict):
        logger.warning("TextWorkflow設定ファイルの形式が不正です（辞書以外）: %s", path)
        return {}

    return data


class ConfigurationResolver:
    """組み込み・個人・ワークスペース・実行時設定をマージする構造体。

    優先度順（DD-003 §4.1、右側優先）:
    `Built-in Defaults` → `User Config` → `Workspace Config` → `Runtime Overrides`

    `personal_config`/`workspace_config` を明示的に注入すればファイルI/Oなしで
    テスト可能な純粋な構造体として振る舞う。実ファイルからの読み込みは
    ``from_app_data_dir()`` で組み立てる Production 経路が担い、ワークスペース
    設定は ``WorkflowRequest.workspace_root`` に応じて呼び出しごとに動的解決
    できるよう ``resolve()`` の引数としても受け付ける。
    """

    def __init__(
        self,
        builtin_config: dict[str, Any] | None = None,
        personal_config: dict[str, Any] | None = None,
        workspace_config: dict[str, Any] | None = None,
    ) -> None:
        self._builtin = builtin_config or DEFAULT_BUILTIN_CONFIG
        self._personal = personal_config or {}
        self._workspace = workspace_config or {}

    @classmethod
    def from_app_data_dir(
        cls,
        app_data_dir: str,
        builtin_config: dict[str, Any] | None = None,
    ) -> ConfigurationResolver:
        """ユーザー設定を実ファイルから読み込んで構築する（Production adapter）。

        ワークスペース設定は構築時ではなく、呼び出しごとに
        ``WorkflowRequest.workspace_root`` を用いて ``resolve()`` が動的に
        読み込む（要求ごとに異なるワークスペースを指定できるようにするため）。

        Args:
            app_data_dir: `.clipWatcher`/`.clipwatcher` 相当のアプリ設定ディレクトリ。
            builtin_config: 組み込み既定値の上書き（主にテスト用）。
        """
        personal_path = os.path.join(app_data_dir, WORKSPACE_CONFIG_FILE_NAME)
        personal_config = load_json_config_file(personal_path)

        return cls(
            builtin_config=builtin_config,
            personal_config=personal_config,
        )

    def resolve(
        self,
        runtime_overrides: dict[str, Any] | None = None,
        workspace_root: str | None = None,
    ) -> dict[str, Any]:
        """優先度に従って設定をディープマージして返す。

        Args:
            runtime_overrides: 呼び出し単位の設定上書き（最優先）。
            workspace_root: 指定された場合、
                `{workspace_root}/.clipwatcher/workflow.json` を動的に読み込み、
                ワークスペース設定として個人設定の上にマージする。
                未指定の場合、コンストラクタに注入済みの ``workspace_config``
                （主にテスト用）を使用する。
        """
        effective = copy.deepcopy(self._builtin)

        workspace_config = self._workspace
        if workspace_root:
            workspace_path = os.path.join(
                workspace_root, WORKSPACE_CONFIG_DIR_NAME, WORKSPACE_CONFIG_FILE_NAME
            )
            workspace_config = load_json_config_file(workspace_path)

        for layer in [self._personal, workspace_config, runtime_overrides or {}]:
            if layer:
                effective = deep_overlay(effective, layer)

        return effective
