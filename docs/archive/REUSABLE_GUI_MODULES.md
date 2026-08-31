---
document_type: archive
status: archived
archived_at: 2026-08-31
current_authority: "現行コードおよびdocs/design/"
reason: "GUIモジュールの再利用性に関する当時の整理を保存するため"
---

# 再利用可能なGUIモジュール一覧

> **アーカイブ資料**: 本書は当時の構成整理であり、現行仕様の正本ではありません。現行コードおよび `docs/design/` を確認してください。

本ドキュメントでは、ClipWatcherプロジェクト内のGUI関連モジュールのうち、他のコンポーネントや将来の拡張、あるいは他のTkinterプロジェクトで流用・再利用が可能なものをまとめます。

## 1. 基盤・ベースクラス (Base Classes)

これらのクラスは、UIの一貫性を保ち、共通の機能（テーマ適用、エラーハンドリング、イベント連携）を提供するための基盤となります。

- **`src/gui/base/base_frame_gui.py` (`BaseFrameGUI`)**
    - `tk.Frame` の拡張。`app_instance` を保持し、エラーハンドリング機能を標準で備えています。
- **`src/gui/base/base_toplevel_gui.py` (`BaseToplevelGUI`)**
    - `tk.Toplevel` の拡張。起動時に自動的に現在のテーマをウィンドウ全体（および子要素）に適用します。
- **`src/gui/base/context_menu.py` (`BaseContextMenu`)**
    - 右クリックメニューの抽象基底クラス。多言語対応（`Translator`）とイベント通知（`EventDispatcher`）の仕組みを統合しており、内容が動的に変化するメニューの実装に適しています。

## 2. 汎用的なUIコンポーネント (Reusable Components)

特定のデータ（履歴や定型文）に依存せず、または疎結合に設計されており、他のプロジェクトでも利用しやすいモジュールです。

- **`src/gui/theme_manager.py` (`ThemeManager`)**
    - **機能**: 明るい/暗いテーマの切り替えを一括管理。
    - **再利用性**: 高い。ttkスタイルと標準Tkinterウィジェットの両方に再帰的に配分を適用するロジックが含まれており、容易に他のアプリに組み込めます。
- **`src/gui/custom_widgets.py` (`ContextMenuMixin`, `CustomEntry`, `CustomText`)**
    - **機能**: 標準の `Entry` や `Text` ウィジェットに「コピー・切り取り・貼り付け・全選択」の右クリックメニューを追加します。
    - **再利用性**: 高い。多言語対応が必要なテキスト入力ウィジェットの標準として流用可能です。

## 3. 疎結合化された特定機能コンポーネント (Specialized Components)

ClipWatcher固有の機能を含みますが、`EventDispatcher` を介した疎結合な設計により、UIのパーツとして独立して扱えるものです。

- **`src/gui/components/history_list_component.py` (`HistoryListComponent`)**
    - クリップボード履歴の表示と検索に特化したリストボックスコンポーネント。
- **`src/gui/components/phrase_list_component.py` (`PhraseListComponent`)**
    - 定型文（テンプレート）の一覧表示と操作用コンポーネント。
- **`src/gui/windows/settings_window.py` (`SettingsWindow`)**
    - 多機能な設定画面。タブ形式のUI構造を他の中規模なアプリケーションの「設定画面」の雛形として流用可能です。

## 流用時の注意点

1. **`app` インスタンスへの依存**: 
   多くのGUIクラスは `src/core/base_application.py` のインスタンス（`app`）をコンストラクタで受け取ります。流用先でも `translator` や `event_dispatcher` などのメンバを持つコンテキストオブジェクトが必要です。
2. **テーマ設定ファイル**: 
   `ThemeManager` は `src/core/config/defaults.py` に記述された `THEMES` 定数を参照します。流用時はこの設定値も合わせて移植（または環境に応じた再定義）が必要です。
