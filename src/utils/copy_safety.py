"""Clipboard copy safety checks for explicitly enabled warnings."""

from __future__ import annotations

import re

RISK_MESSAGES: dict[str, str] = {
    "multiple_lines": "実行可能な内容が複数行あります",
    "command_chain": "コマンド連結構文（;、&&、||）が含まれています",
    "destructive_command": "削除・初期化などの破壊的な操作が含まれています",
    "download_execute": "ダウンロードした内容を直接実行する構文が含まれています",
    "privilege_escalation": "権限昇格を行う構文が含まれています",
}

_COMMAND_LINE_PATTERN = re.compile(
    r"^\s*(?:[$>]\s*)?(?:"
    r"sudo|runas|rm|dd|mkfs|del|rmdir|remove-item|format|git|curl|wget|"
    r"python(?:\.exe)?|pip(?:\.exe)?|npm|npx|docker|kubectl|echo|set|"
    r"cd|mkdir|copy|move|powershell|pwsh|bash|sh)\b",
    re.IGNORECASE,
)
_COMMAND_CHAIN_PATTERN = re.compile(r";|&&|\|\||(?<!\|)\|(?!\|)")
_DESTRUCTIVE_PATTERN = re.compile(
    r"(?:"
    r"\brm\s+-[^\n]*\brf\b|"
    r"\bsudo\s+rm\b|"
    r"\bdd\s+[^\n]*\bof=|"
    r"\bmkfs(?:\.[\w-]+)?\b|"
    r"\bdel\s+/[sp]\b|"
    r"\brmdir\s+/s\b|"
    r"\bremove-item\s+[^\n]*-recurse\b|"
    r"\bformat(?:\.com)?\s+[a-z]:|"
    r"\bgit\s+reset\s+--hard\b|"
    r"\bgit\s+clean\s+-[^\n]*\bf\b"
    r")",
    re.IGNORECASE,
)
_DOWNLOAD_EXECUTE_PATTERN = re.compile(
    r"\b(?:curl|wget)\b[^\n]*\|\s*(?:sh|bash|zsh|pwsh|powershell)\b",
    re.IGNORECASE,
)
_PRIVILEGE_ESCALATION_PATTERN = re.compile(r"\b(?:sudo|runas)\b", re.IGNORECASE)


def _has_multiple_executable_lines(text: str) -> bool:
    executable_lines = [
        line for line in text.splitlines() if _COMMAND_LINE_PATTERN.search(line)
    ]
    return len(executable_lines) >= 2


def analyze_copy_risks(text: str) -> list[str]:
    """Return stable risk category keys found in clipboard text.

    This function does not execute, normalize, or modify the input text. It is
    intentionally conservative: detection only supports a confirmation dialog.
    """
    if not isinstance(text, str) or not text:
        return []

    risks: list[str] = []
    if _has_multiple_executable_lines(text):
        risks.append("multiple_lines")
    if _COMMAND_CHAIN_PATTERN.search(text):
        risks.append("command_chain")
    if _DESTRUCTIVE_PATTERN.search(text):
        risks.append("destructive_command")
    if _DOWNLOAD_EXECUTE_PATTERN.search(text):
        risks.append("download_execute")
    if _PRIVILEGE_ESCALATION_PATTERN.search(text):
        risks.append("privilege_escalation")
    return risks
