# ClipWatcher: クリップボード履歴ツール

## プロジェクト概要
ClipWatcherは、ユーザーのクリップボードを自動的に監視し、履歴を管理・再利用できるようにするデスクトップアプリケーションです。PythonとTkinterを使用して開発されています。

## プロジェクト構造
```
Clip_Watcher/
├── clip_watcher.py       # メイン実行ファイル
├── requirements.txt      # 依存ライブラリ
├── README.md             # プロジェクト説明
├── SPECIFICATION.md      # 詳細な仕様書と将来の機能拡張計画
└── src/
    ├── __init__.py       # Pythonパッケージとして認識させるためのファイル
    ├── clipboard_monitor.py # クリップボード監視ロジック
    ├── gui/              # GUI関連モジュール
    │   ├── __init__.py
    │   └── main_gui.py   # メインGUIの構築
    └── event_handlers/   # イベントハンドラ関連モジュール
        ├── __init__.py
        └── main_handlers.py # 主要なイベントハンドラ
```

## 開発環境

  * **言語**: Python 3.x
  * **GUIライブラリ**: Tkinter (Python標準ライブラリ)
  * **外部ライブラリ**:
      * **`Pillow`**: 画像の表示と操作 (将来的な機能拡張用)
      * **`keyboard`**: グローバルホットキーの監視 (将来的な機能拡張用)

## 実行方法
1. 依存ライブラリをインストールします。
   ```bash
   pip install -r requirements.txt
   ```
2. メインファイルを実行します。
   ```bash
   python clip_watcher.py
   ```

## 注意事項
- 一部の環境やセキュリティ設定によっては、クリップボードアクセスが制限される場合があります。
- 本プロジェクトは基本的な機能を提供するものであり、実際の利用にあたっては、セキュリティやプライバシーに十分注意を払ってください。

## 詳細な仕様と機能拡張計画
より詳細な機能一覧、UI/UX、メニューバーの項目、拡張性に関するアプローチについては、[SPECIFICATION.md](SPECIFICATION.md) を参照してください。
