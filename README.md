# ClipWatcher: クリップボード履歴ツール

## プロジェクト概要
ClipWatcherは、ユーザーのクリップボードを自動的に監視し、履歴を管理・再利用できるようにするデスクトップアプリケーションです。Python (Tkinter) と SQLite を使用して、堅牢なデータ保存と柔軟な拡張（プラグイン機能）を提供します。

## 主な機能
- **クリップボード履歴:** クリップボードのテキスト履歴を自動的に記録・SQLiteに保存します。
- **メタ管理・定型文:** カテゴリやタグ付きの定型文を管理し、簡単にコピーできます。
- **履歴のピン留め:** 重要な履歴項目をリストの上部にピン留めし、削除から保護します。
- **リアルタイム検索:** 履歴をリアルタイムで検索・フィルタリングできます。
- **拡張プラグイン機能:** クリップボード内容のフォーマット変換や、追加のGUIツールタブを提供するプラグインシステムを搭載しています。
- **コンテキストメニュー:** 右クリックメニューから、コピー、削除、ピン留め、カテゴリ移動などの操作が可能です。
- **テーマ切り替え:** ライトモードとダークモードのテーマを切り替えられます。

## プロジェクト構造
現在のアーキテクチャでは、関心の分離（ビジネスロジックとGUIの分離）を徹底し、コア層はサブモジュール化されています。

```
Clip_Watcher/
├── clip_watcher.py             # アプリケーションのエントリーポイント
├── pyproject.toml              # setuptools のプロジェクト設定・依存関係
├── src/
│   ├── core/                   # コア機能
│   │   ├── bootstrap/          # アプリケーション起動と依存性注入
│   │   ├── clipboard/          # クリップボード監視機能
│   │   ├── events/             # イベントディスパッチャおよびコマンド
│   │   └── config/             # 設定管理
│   ├── db/                     # SQLiteデータベース操作・DAO・DTO
│   ├── services/               # ビジネスロジック層 (HistoryService等)
│   ├── gui/                    # GUI関連 (Tkinter / ttk)
│   ├── event_handlers/         # UIアクションとロジックを繋ぐハンドラ群
│   ├── plugins/                # 拡張プラグイン (テキスト変換 / GUIツール)
│   └── utils/                  # ユーティリティ (ログ設定、エラー処理)
├── docs/                       # 設計・運用・how-to・アーカイブ資料
└── tests/                      # テストコード (pytest)
```

## 開発環境

- **言語**: Python 3.10+
- **GUIライブラリ**: Tkinter / ttk (Python標準ライブラリ)
- **データベース**: SQLite (Python内蔵 `sqlite3`)
- **外部ライブラリ**: `psutil`, `pywin32` など

## セットアップと実行

1. 実行用の依存関係をインストールします。
   ```bash
   python -m pip install -e .
   ```
2. メインファイルを実行します。
   ```bash
   python clip_watcher.py
   ```

## 開発時の検証

開発用依存関係を含めてインストールします。

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest
```

CI では同等の検証を `uv` 経由で実行します。

## 詳細なドキュメント

より詳細な設計・運用資料は `docs/` を参照してください。

- [全体アーキテクチャ基本設計書（CLW-BD-001）](docs/design/CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md)
- [機能基本設計書（CLW-BD-002）](docs/design/CLW-BD-002_ClipWatcher機能基本設計書.md)
- [設定画面・グローバルホットキー詳細設計書（CLW-DD-001）](docs/design/CLW-DD-001_設定画面スキーマ駆動化とグローバルホットキー連携詳細設計書.md)
- [コア層起動監視イベント制御詳細設計書（CLW-DD-002）](docs/design/CLW-DD-002_コア層起動監視イベント制御詳細設計書.md)
- [TextWorkflow詳細設計書（CLW-DD-003）](docs/design/CLW-DD-003_TextWorkflow詳細設計書.md)
- [開発環境セットアップ](docs/setup/toml_project_setup.md)
- [Text Workflow 分類ルールガイド](docs/how-to/HOWTO_TEXT_WORKFLOW_RULES.md)

## 注意事項
- 一部の環境やセキュリティ設定によっては、クリップボードアクセスが制限される場合があります。
- 本プロジェクトは利便性向上を目的としており、パスワードなど極秘情報の取り扱いについてはユーザー自身の責任で管理・除外設定を利用してください。
