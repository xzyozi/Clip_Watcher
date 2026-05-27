# ClipWatcher アーキテクチャレビュー (2026-02-28)

本ドキュメントでは、ClipWatcherプロジェクト全体のアーキテクチャアーキテクチャ設計・実装に対するレビュー結果をまとめます。

## 1. 優れた点（Strengths）

現在のアーキテクチャには、アプリケーションの拡張性や保守性を高めるための多くの優れた設計パターンが組み込まれています。

- **EventDispatcherによる疎結合化**:
  `src/core/event_dispatcher.py` を中心としたPub/Subパターンの導入により、GUIレイヤーとバックグラウンド処理（ClipboardMonitor）、そしてイベントアクション（EventHandlers）が直接的な依存関係を持たずに通信できています。これにより、今後のモジュール追加が容易になっています。
- **CommandパターンとUndoManager**:
  履歴アイテムに対するフォーマット適用や編集などの破壊的な変更を `UpdateHistoryCommand` としてカプセル化している点は非常に優れています。これにより、複雑になりがちな「元に戻す（Undo）」の実装がシンプルかつ安全に実現されています。
- **プラグインアーキテクチャ**:
  `PluginManager` を通じてフォーマッターやGUIツールを動的に読み込む仕組みは、コア機能を汚染することなくアプリケーションを拡張できる強力な仕組みです。
- **ApplicationBuilderの採用**:
  オブジェクトの生成プロセスをカプセル化し、依存関係を明確にしてから `MainApplication` を起動するフローが確立されており、将来的なDI (Dependency Injection) コンテナ導入への足がかりとして機能しています。

## 2. 改善提案（Areas for Improvement）

よりスケーラブルでテストが容易なコードベースへと進化させるために、以下のアーキテクチャ上の改善点を提案します。

### 2.1 ClipboardMonitorの単一責任原則 (SRP) 違反の解消
現在、`src/core/clipboard_monitor.py` 内の `ClipboardMonitor` クラスが以下の複数の責任を負っています。
1. OSのクリップボードの監視（`tk.clipboard_get` や `win32clipboard` との対話）
2. 履歴（History）のリスト管理、ピン留め、履歴上限の制御
3. 履歴ファイルの永続化（`history.json` への読み書き）

**提案**:
- 状態管理と永続化を行う `HistoryManager` （または `HistoryRepository`）クラスを分離すべきです。
- `ClipboardMonitor` は純粋にOSクリップボードの変化を検知して `EventDispatcher` で通知するだけの役割とし、データの持ち込みは `HistoryManager` に任せることで、責務が明確になりテスト容易性が劇的に向上します。

### 2.2 GUIとCoreの暗黙的な状態同期
`MainApplication` および `EventHandlers` において、変更があった際に直接 `self.app.gui.update_clipboard_display()` などを呼び出してUIを強制更新している箇所が散見されます。

**提案**:
- 現在の `EventDispatcher` をさらに推し進め、単一方向データフロー（Unidirectional Data Flow）を導入することをお勧めします。
- 例えば、`HistoryManager` 内のデータが変更されたら常に `HISTORY_STATE_UPDATED` イベントを発火し、GUI側 (`main_gui.py`) がそのイベントを購読して自身の表示を更新するようにすれば、コマンドやハンドラが直接GUIコンポーネントを操作するコードを削減できます。

### 2.3 MainApplicationへの依存とカプセル化
`src/event_handlers` 配下の多くのハンドラが `self.app`（`MainApplication`のインスタンス）全体への直接アクセスを持っています。これにより、ハンドラからアプリケーション全体のあらゆる状態・メソッドにアクセス可能であり、予期せぬ副作用を生むリスクがあります。

**提案**:
- ハンドラには `MainApplication` 全体を渡すのではなく、必要なユースケース（例えば `clipboard_monitor` や `undo_manager` など個別の依存）のみを注入するか、あるいはイベントデータ自体に操作対象の情報を乗せるインターフェース設計にすることで、結合度を下げることができます。

### 2.4 テスト容易性 (Testability)
現在、`ClipboardMonitor` のポーリングロジックが `tk_root.after` を前提にしているため、TkinterのメインループがないCLI環境や単体テストにおいて、ビジネスロジックだけをテストするのが困難な構造になっています。

**提案**:
- 非同期ループやタイマー駆動部分をインターフェース化し、モック可能な `Scheduler` や `Timer` に置き換え可能にすることで、UIレスの環境でもコアロジックの100%の単体テストが可能になります。

## 3. 次のステップ（Next Steps）

もしアーキテクチャの改善に着手される場合、リスクが少なく効果が高い以下の順番でのリファクタリングを推奨します。

1. **`ClipboardMonitor` からの `HistoryManager` の分離**（SRPの確立）
2. イベントハンドラにおける `self.app` アクセスの段階的な削減
3. タイマー処理とTkinterの分離による単体テスト基盤の導入

---
*レビュー担当: AI Assistant*
