# 依存関係の管理フロー

このプロジェクトの依存関係の正本は、リポジトリルートの `pyproject.toml` です。ビルドバックエンドには `setuptools.build_meta` を使用し、Python 3.10 以降を対象とします。

---

## 1. 依存関係の定義

| 種別     | 定義場所                              | 用途                                         |
| :------- | :------------------------------------ | :------------------------------------------- |
| 実行依存 | `[project].dependencies`              | アプリケーションの実行に必要なライブラリ     |
| 開発依存 | `[project.optional-dependencies].dev` | テスト、静的解析、整形確認に必要なライブラリ |

`requirements.in`、`requirements.txt`、`pip-tools`、`setup.py` はこのプロジェクトの依存管理には使用しません。

現在の実行依存は `Pillow`、`pywin32`、`psutil` です。開発依存は `.[dev]` のextrasとしてインストールします。

---

## 2. 新しいライブラリを追加する手順

1. 追加の必要性、ライセンス、保守状況を確認します。名前が類似した別パッケージを選ばないよう、公式配布元も確認してください。
2. 実行時に必要な場合は `[project].dependencies`、開発時だけに必要な場合は `[project.optional-dependencies].dev` へ追加します。
3. 新規依存には、再現可能な正確なバージョンを指定します。

   ```toml
   [project]
   dependencies = [
       "example-package==1.2.3",
   ]
   ```

4. editable installをやり直し、追加した依存を利用する機能と既存機能を確認します。
5. `pyproject.toml` の変更だけを対象にしてコミットします。生成済みrequirementsファイルは作成しません。

---

## 3. 新しい開発環境をセットアップする手順

1. リポジトリをクローンします。

   ```bash
   git clone <repository-url>
   cd Clip_Watcher-develop
   ```

2. 仮想環境を作成して有効化します（推奨）。

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. アプリケーションだけを利用する場合は、editable installを実行します。

   ```powershell
   python -m pip install -e .
   ```

4. 開発、テスト、静的解析も行う場合は、開発用extrasを含めてインストールします。

   ```powershell
   python -m pip install -e ".[dev]"
   ```

データベースはアプリケーション起動時に初期化されるため、別途 `setup.py` やフロントエンドビルドを実行する必要はありません。

---

## 4. CIでの依存導入と検証

GitHub Actionsでは `uv` を使用し、次の順で検証します。

```powershell
uv pip install --system -e ".[dev]"
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

ローカルでは、必要に応じて同じ検証コマンドを `uv` で実行するか、仮想環境にインストール済みの各ツールを実行してください。
