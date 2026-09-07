# 保守性・提供モジュール基盤レビュー報告書

作成日: 2026年8月31日
対象: 現行HEAD（差分ではないベースラインレビュー）
対象領域: パッケージ化、公開インターフェース、TextWorkflow、CI、テスト、プラグイン

---

## 1. 結論

ClipWatcherはデスクトップアプリとして層分割、DI、品質ゲートを備える一方、外部へ提供・再利用するモジュールとしては、公開インターフェース、配布入口、外部依存とのseam、再現可能な依存管理が未確立である。まず同一配布物内でTextWorkflowを独立可能な深いモジュールへ整備し、外部利用の確定後に別パッケージ化を判断する。

## 2. Standards（規約・保守性）

### 文書化された方針との不整合

1. `docs/setup/dependency_management.md` は完全ピンを求めるが、`pyproject.toml` の実行・開発・build依存は完全ピンではない。
2. 同文書は `pyproject.toml` を唯一の正本としlockファイルを持ち込まない方針だが、`uv.lock` と `requirements.txt` が存在する。CI（`.github/workflows/ci.yml`）も `uv.lock` を使わずに依存導入する。
3. `pyproject.toml` に `[project.scripts]` がなく、安定した実行入口・公開import名前空間が定義されていない。

### 設計上の判断事項

- `clip_watcher.py` は `src.*` import と `sys.path` 操作に依存し、インストール後の利用や名前空間変更に弱い。
- `MainApplication` はGUI、イベント、設定、ホットキー、貼り付け、終了処理を持ち、変更の局所性が低い。
- `ClipboardMonitor` はTk、Win32 API、DB、通知、スレッドを直接扱い、OS・GUI・永続化を置換するseamが不足する。
- `PluginManager` は内蔵パッケージを反射的に探索して無引数生成し、外部提供プラグインの発見・DI・互換性判定に対応しない。

## 3. Spec（設計書との適合）

対象仕様は `docs/design/CLW-DD-003_TextWorkflow詳細設計書.md` と `docs/design/CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md` である。

### 未実装・部分実装

1. DD-003 §4.1 が定める既定値→ユーザー→ワークスペース→実行時上書きの設定ファイル解決は未実装で、`ConfigurationResolver` は注入辞書をマージするのみである。
2. DD-003 §5.2 の `ApplicationBuilder` 登録とGUI・コマンドハンドラへの `TextWorkflowService` 注入がない。
3. DD-003 §4.5 の永続化された専用履歴、保持上限、期限パージがない。既定履歴は `:memory:` である。
4. DD-003 §6 の正規表現パターン長・実行時間制限がなく、ReDoS対策が未実装である。

### 不整合

- DD-003 §5.3 は `EventDispatcher` 経由でUIスレッドへ通知する方針だが、`TextWorkflowService` はワーカースレッドからcallbackを直接呼ぶ。
- DD-003 の `~/.clip_watcher`、BD-001 の `.clipWatcher`／`.clipwatcher`、実装の保存先が一致しない。

## 4. 推奨アーキテクチャ

`TextWorkflow` を `clip_watcher.workflow` として公開し、呼び出し側は `engine.execute(request) -> result` の小さなInterfaceだけを利用する。分類、テンプレート展開、正規化、失敗契約は内部Implementationへ隠蔽する。

設定は `WorkflowConfigSource`、履歴は `ExecutionHistoryStore`、GUIへの結果通知は `WorkflowResultNotifier` をInterfaceとし、ファイル設定・SQLite・TkinterをそれぞれProduction adapterとして実装する。テストはインメモリアダプターを使う。ClassifierとNormalizerはTextWorkflow内部に保ち、不要な抽象化を避ける。

起動・GUI・Windows連携は `clip_watcher.app` に隔離し、`[project.scripts]` で `clip-watcher = "clip_watcher.app.main:main"` のような実行入口を提供する。`src` を実パッケージ名として公開せず、`sys.path` 操作を廃止する。

## 5. 実施優先順位

1. 公開する型・関数・例外と互換性ポリシーを決定する。
2. 実パッケージ名、`[project.scripts]`、依存管理の正本とlock方針を確定する。
3. TextWorkflowの設定・履歴・UI通知のseamとProduction/Test adapterを実装する。
4. 設定保存先、保持・パージ、ReDoS対策、失敗契約を設計書と実装で同時に確定する。
5. wheel/sdistビルド、クリーン環境インストール、CLI起動、公開Interfaceの利用例をCIで検証する。
6. 外部利用が確定した場合だけ、TextWorkflowの別配布物化と外部プラグイン登録方式を検討する。

## 6. 検証結果

既存 `.venv` で実行した結果はすべて成功した。

- `ruff check .`: 成功
- `ruff format --check .`: 156 files already formatted
- `mypy .`: 96 source files、問題なし
- `pytest`: 98 passed（2.85秒）

`uv run` はPyPIから `setuptools>=61.0` を取得する際に `invalid peer certificate: UnknownIssuer` で失敗した。これはコード不具合ではなく、端末のTLS証明書チェーンまたはプロキシ設定によりネットワーク検証が中断したものである。
