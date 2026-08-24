from __future__ import annotations

import re
from datetime import datetime
from typing import Any


class TemplateError(Exception):
    """テンプレート処理のエラー"""

    pass


class TemplateRenderer:
    """テンプレートに変数を展開するレンダラー"""

    def __init__(self, templates: list[dict[str, Any]] | None = None) -> None:
        self._templates_by_id = {t["id"]: t for t in (templates or []) if "id" in t}

    def render(
        self,
        template_id: str | None,
        variables: dict[str, Any],
        default_body: str | None = None,
    ) -> str:
        """
        指定された template_id のテンプレートに変数を埋め込んでテキストを返す。
        template_id が未指定または見つからない場合、default_body または variables['input'] をそのまま返す。
        """
        if not template_id or template_id not in self._templates_by_id:
            if default_body is not None:
                return default_body
            return str(variables.get("input", ""))

        template_def = self._templates_by_id[template_id]
        body: str = template_def.get("body", "")
        template_vars: list[dict[str, Any]] = template_def.get("variables", [])

        # 標準環境変数の補填
        full_vars = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **variables,
        }

        # 変数展開と必須チェック
        for var_def in template_vars:
            name = var_def.get("name")
            if not isinstance(name, str):
                continue
            required = var_def.get("required", False)
            default_val = var_def.get("default", "")

            if name not in full_vars or full_vars[name] is None:
                if required:
                    raise TemplateError(
                        f"Required variable '{name}' is missing for template '{template_id}'"
                    )
                full_vars[name] = default_val

        # 置換処理 {{variable}}
        def replace_match(match: re.Match[str]) -> str:
            var_name = match.group(1).strip()
            return str(full_vars.get(var_name, f"{{{{{var_name}}}}}"))

        return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replace_match, body)
