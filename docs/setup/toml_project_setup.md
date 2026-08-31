# `pyproject.toml` によるプロジェクトセットアップガイド

このプロジェクトは、`pyproject.toml` をパッケージメタデータと依存関係の正本として使用します。ビルドバックエンドは `setuptools.build_meta` です。Hatch、`setup.py`、Playwright、requirementsファイルの生成は利用しません。

---

## 1. 前提条件

- Python 3.10 以降
- Git
- 開発・CIと同じコマンドを使う場合は [uv](https://docs.astral.sh/uv/)（任意）

---

## 2. 開発環境の作成

リポジトリのルートで、仮想環境を作成して有効化します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

PowerShellの実行ポリシーにより有効化できない場合は、現在のシェルに限って次のコマンドを実行してから再試行します。

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## 3. パッケージのインストール

アプリケーションの実行に必要な依存だけをインストールする場合は、次を実行します。

```powershell
python -m pip install -e .
```

開発用のテスト・静的解析ツールも含める場合は、`dev` extrasを指定します。

```powershell
python -m pip install -e ".[dev]"
```

editable installのため、`src/` 配下のソースを変更した後にパッケージを再インストールする必要はありません。依存定義を変更した場合だけ、該当するインストールコマンドを再実行してください。

---

## 4. 検証コマンド

CIでは `uv` を用いて、次のコマンドを実行します。

```powershell
uv pip install --system -e ".[dev]"
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

ローカルでも `uv` を導入している場合は同じコマンドを利用できます。導入していない場合は、仮想環境を有効化したうえで `ruff check .`、`ruff format --check .`、`mypy .`、`pytest` を実行してください。
