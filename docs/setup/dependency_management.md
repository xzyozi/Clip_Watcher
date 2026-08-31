---
document_type: operation
updated_at: 2026-08-31
canonical_source: pyproject.toml
---

# 依存関係の管理フロー

依存関係の正本はリポジトリルートの `pyproject.toml` です。Python 3.10 以降を対象とし、ビルドバックエンドには `setuptools.build_meta` を使用します。環境構築、仮想環境、インストール、ローカル検証の手順は [toml_project_setup.md](toml_project_setup.md) を参照してください。

## 1. 依存関係の定義

| 種別     | 定義場所                              | 用途                                         |
| :------- | :------------------------------------ | :------------------------------------------- |
| 実行依存 | `[project].dependencies`              | アプリケーション実行に必要なライブラリ       |
| 開発依存 | `[project.optional-dependencies].dev` | テスト、静的解析、整形確認に必要なライブラリ |

`requirements.in`、`requirements.txt`、`pip-tools`、`setup.py` は依存管理に使用せず、生成もしません。実行依存は `Pillow`、`pywin32`、`psutil`、開発依存は `dev` extras を正本とします。

## 2. 依存関係を追加・更新する方針

1. 必要性、公式配布元、ライセンス、保守状況、既知の互換性を確認し、類似名のパッケージを追加しません。
2. 実行時に必要なものは `[project].dependencies`、開発時だけに必要なものは `[project.optional-dependencies].dev` に追加します。
3. 新規・更新する依存は必ず完全ピン（`==`）にします。範囲指定、最新指定、間接依存だけへの依存は使用しません。

```toml
[project]
dependencies = [
    "example-package==1.2.3",
]
```

4. `pyproject.toml` の変更後は [toml_project_setup.md](toml_project_setup.md) の該当インストール手順を再実行し、追加機能と既存機能を検証します。
5. 依存定義の変更と検証結果をレビュー可能な単位で記録します。requirements ファイルは追加しません。

## 3. CI の依存導入・品質ゲート

CI の正本は [ci.yml](../../.github/workflows/ci.yml) です。`windows-latest` で `pyproject.toml` が指定する Python をセットアップし、`uv pip install --system -e ".[dev]"` により開発依存を導入します。その後、`ruff check .`、`ruff format --check .`、`mypy .`、`pytest` を順に実行します。

依存を追加・更新した変更は、上記すべてが成功することを受け入れ条件とします。CI と異なる依存導入方法やロックファイルを持ち込まず、CI のコマンド変更が必要な場合は `ci.yml` と本書を同時に見直します。

## 改訂履歴

| 日付       | 変更内容                                                                                                                |
| :--------- | :---------------------------------------------------------------------------------------------------------------------- |
| 2026-08-31 | 軽量メタデータと改訂履歴を追加し、環境構築手順を TOML セットアップ文書へ委譲。依存追加、完全ピン、CI 方針に内容を集約。 |
