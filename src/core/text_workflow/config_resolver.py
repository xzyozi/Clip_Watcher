from __future__ import annotations

import copy
from typing import Any

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


class ConfigurationResolver:
    """組み込み・個人・ワークスペース・実行時設定をマージする構造体"""

    def __init__(
        self,
        builtin_config: dict[str, Any] | None = None,
        personal_config: dict[str, Any] | None = None,
        workspace_config: dict[str, Any] | None = None,
    ) -> None:
        self._builtin = builtin_config or DEFAULT_BUILTIN_CONFIG
        self._personal = personal_config or {}
        self._workspace = workspace_config or {}

    def resolve(
        self, runtime_overrides: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """優先度に従って設定をディープマージして返す"""
        effective = copy.deepcopy(self._builtin)

        for layer in [self._personal, self._workspace, runtime_overrides or {}]:
            if layer:
                effective = deep_overlay(effective, layer)

        return effective
