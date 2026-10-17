from __future__ import annotations

import copy
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

WORKSPACE_CONFIG_DIR_NAME = ".clipwatcher"
WORKSPACE_CONFIG_FILE_NAME = "workflow.json"

#: ワークスペース設定（信頼できないリポジトリ由来になり得る）から「緩める」ことを
#: 禁止するセキュリティ関連パラメータ（`workflow` 配下）。厳しくする方向（より小さい値）の
#: 上書きだけを許可する。
WORKSPACE_PROTECTED_WORKFLOW_KEYS = (
    "maxInputBytes",
    "classifierRegexMaxPatternLength",
    "classifierRegexTimeoutSeconds",
)

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
        # ReDoS対策（DD-003 §7）: 分類ルールの regex パターン長・実行時間の上限。
        "classifierRegexMaxPatternLength": 200,
        "classifierRegexTimeoutSeconds": 0.5,
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


def is_safe_workspace_root(workspace_root: str) -> bool:
    """ワークスペース設定を読み込んでよい `workspace_root` かを判定する。

    UNC パス（``\\\\host\\share`` / ``//host/share``）は、ファイルアクセスの時点で
    NTLM 認証情報が外部ホストへ送出され得るため、ファイルシステムへ触れる前に拒否する。
    また、ローカルに実在する絶対パスのディレクトリのみ許可する。
    """
    if not isinstance(workspace_root, str) or not workspace_root:
        return False
    if workspace_root.startswith(("\\\\", "//")):
        return False
    if not os.path.isabs(workspace_root):
        return False
    return os.path.isdir(workspace_root)


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _restrict_workspace_security_params(
    workspace_config: dict[str, Any], trusted_workflow: dict[str, Any]
) -> dict[str, Any]:
    """ワークスペース設定のセキュリティ関連パラメータを「厳しくする方向」に限定する。

    信頼できる層（組み込み・個人設定）の値以下の正の数値のみ採用し、それ以外
    （緩める値、不正な型、信頼側に基準値がないもの）は取り除いて信頼側の値を維持する。
    """
    workflow = workspace_config.get("workflow")
    if not isinstance(workflow, dict):
        return workspace_config

    sanitized = copy.deepcopy(workspace_config)
    sanitized_workflow: dict[str, Any] = sanitized["workflow"]
    for key in WORKSPACE_PROTECTED_WORKFLOW_KEYS:
        if key not in sanitized_workflow:
            continue
        value = sanitized_workflow[key]
        trusted_value = trusted_workflow.get(key)
        if (
            _is_positive_number(value)
            and _is_positive_number(trusted_value)
            and value <= trusted_value
        ):
            continue
        logger.warning(
            "ワークスペース設定の '%s' は信頼側の値を緩める/不正なため無視しました。",
            key,
        )
        del sanitized_workflow[key]
    return sanitized


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
        if self._personal:
            effective = deep_overlay(effective, self._personal)

        workspace_config = self._workspace
        if workspace_root:
            if is_safe_workspace_root(workspace_root):
                workspace_path = os.path.join(
                    workspace_root,
                    WORKSPACE_CONFIG_DIR_NAME,
                    WORKSPACE_CONFIG_FILE_NAME,
                )
                workspace_config = load_json_config_file(workspace_path)
            else:
                logger.warning(
                    "workspace_root が安全でないためワークスペース設定を読み込みません"
                    "（UNC パス、相対パス、または存在しないディレクトリ）"
                )
                workspace_config = {}

        if workspace_config:
            trusted_workflow = effective.get("workflow")
            workspace_config = _restrict_workspace_security_params(
                workspace_config,
                trusted_workflow if isinstance(trusted_workflow, dict) else {},
            )
            effective = deep_overlay(effective, workspace_config)

        if runtime_overrides:
            effective = deep_overlay(effective, runtime_overrides)

        return effective
