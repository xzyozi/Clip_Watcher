---
document_type: operation
updated_at: 2026-08-31
canonical_source: pyproject.toml
---

# `pyproject.toml` によるプロジェクトセットアップガイド

このプロジェクトは `pyproject.toml` をパッケージメタデータと依存関係の正本として使用します。ビルドバックエンドは `setuptools.build_meta` です。Hatch、`setup.py`、Playwright、requirements ファイルの生成は利用しません。

## 1. 前提条件

- Python 3.10 以降
- Git
- 開発・CI と同じコマンドを使う場合は [uv](https://docs.astral.sh/uv/)（任意）

## 2. 開発環境の作成

リポジトリのルートで仮想環境を作成して有効化します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

PowerShell の実行ポリシーにより有効化できない場合は、現在のシェルに限って次を実行してから再試行します。

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 3. パッケージのインストール

アプリケーションに必要な依存だけを導入する場合は、次を実行します。

```powershell
python -m pip install -e .
```

開発用のテスト・静的解析ツールも導入する場合は、`dev` extras を指定します。

```powershell
python -m pip install -e ".[dev]"
```

editable install のため、`src/` 配下のソースを変更した後に再インストールは不要です。依存定義を変更したときだけ、該当するインストールコマンドを再実行してください。依存を追加・更新する規約は [dependency_management.md](dependency_management.md) を参照してください。

## 4. 検証コマンド

CI は `windows-latest` 上で `uv` を使用し、次を実行します。

```powershell
uv pip install --system -e ".[dev]"
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

ローカルで `uv` を利用できる場合は同じコマンドを使用できます。利用しない場合は仮想環境を有効化してから、`ruff check .`、`ruff format --check .`、`mypy .`、`pytest` を実行してください。

## 改訂履歴

| 日付       | 変更内容                                                                                 |
| :--------- | :--------------------------------------------------------------------------------------- |
| 2026-08-31 | 軽量メタデータと改訂履歴を追加し、依存管理文書との責務境界と現行 CI の実行環境を明確化。 |
