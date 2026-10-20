"""src/core/platform/startup_python.py

自動起動で使う Python 実行ファイルを選ぶ共通処理（Issue #209）。

プロジェクト直下の仮想環境があればそれを優先し、無い（または実体が無い）場合は
呼び出し元が渡す fallback（通常は現在実行中の Python）を使う。
macOS など ``.venv`` を使わない環境でも、まず起動できることを優先する。

選択は自動起動を有効化した時点で行う。有効化後に仮想環境を削除すると、
登録済みの起動設定は壊れる。
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

VENV_DIR_NAMES: tuple[str, ...] = (".venv", "venv")


def venv_python_candidates(
    project_root: Path, relative_executables: Iterable[str]
) -> list[Path]:
    """仮想環境内の Python 実行ファイルの候補を優先順に返す。

    Args:
        project_root: ``clip_watcher.py`` があるプロジェクトルート。
        relative_executables: 仮想環境ディレクトリからの相対パス
            （例: ``"Scripts/pythonw.exe"``、``"bin/python"``）。
    """
    return [
        project_root / venv_name / relative
        for venv_name in VENV_DIR_NAMES
        for relative in relative_executables
    ]


def resolve_python_executable(
    project_root: Path,
    relative_executables: Iterable[str],
    fallback: str,
) -> str:
    """実在する仮想環境の Python を優先し、無ければ fallback を返す。"""
    for candidate in venv_python_candidates(project_root, relative_executables):
        if candidate.is_file():
            return str(candidate)
    return fallback
