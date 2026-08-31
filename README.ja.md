# ClipWatcher 📋

> **Python・Tkinter・SQLiteで構築した、ローカル完結型のクリップボード履歴管理・Text Workflow自動化ツールです。**

[English](./README.md) | [日本語](./README.ja.md)

[![CI](https://github.com/xzyozi/Clip_Watcher/actions/workflows/ci.yml/badge.svg)](https://github.com/xzyozi/Clip_Watcher/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

## 概要

ClipWatcherはクリップボードの変更を監視し、再利用できるテキスト履歴をローカルに保存するデスクトップアプリケーションです。高速検索、ピン留め、定型文管理、テーマ設定、拡張可能なテキスト処理プラグインを提供します。

## 主な機能

- **クリップボード履歴**: コピーしたテキストをSQLiteへ自動記録します。
- **検索・フィルタリング**: 入力に応じて履歴を絞り込みます。
- **履歴のピン留め**: 頻繁に使う項目を先頭に固定し、一括削除から保護します。
- **メタ管理・定型文**: カテゴリ単位で定型文を管理し、すばやくコピーできます。
- **プラグイン**: テキスト変換や追加GUIツールタブを拡張できます。
- **Undo / Redo**: 対応する履歴変更をコマンドパターンで取り消し・やり直しできます。
- **外観・プライバシー設定**: ライト／ダークテーマ、常に手前に表示、履歴上限、除外アプリ設定を提供します。

## 動作要件

- Python 3.10 以降
- Windowsを主な対象とし、Windowsのクリップボード連携には `pywin32` を使用します。

## セットアップと実行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python clip_watcher.py
```

開発用ツールも導入する場合は、`dev` extrasを指定します。

```powershell
python -m pip install -e ".[dev]"
```

## 開発時の検証

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest
```

GitHub ActionsのCIでは、`uv` を通じて同等のlint、フォーマット確認、型検査、テストを実行します。

## ドキュメント

- [全体アーキテクチャ基本設計書（CLW-BD-001）](docs/design/CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md)
- [機能基本設計書（CLW-BD-002）](docs/design/CLW-BD-002_ClipWatcher機能基本設計書.md)
- [設定画面・グローバルホットキー詳細設計書（CLW-DD-001）](docs/design/CLW-DD-001_設定画面スキーマ駆動化とグローバルホットキー連携詳細設計書.md)
- [コア層起動監視イベント制御詳細設計書（CLW-DD-002）](docs/design/CLW-DD-002_コア層起動監視イベント制御詳細設計書.md)
- [TextWorkflow詳細設計書（CLW-DD-003）](docs/design/CLW-DD-003_TextWorkflow詳細設計書.md)
- [開発環境セットアップ](docs/setup/toml_project_setup.md)
- [Text Workflow 分類ルールガイド](docs/how-to/HOWTO_TEXT_WORKFLOW_RULES.md)

## プライバシーとセキュリティ

クリップボード履歴には機密情報が含まれる可能性があります。パスワード管理ソフトなど、履歴を記録すべきでないアプリケーションは除外設定を使用してください。ローカルのセキュリティポリシーによっては、クリップボードへのアクセスが制限される場合があります。
