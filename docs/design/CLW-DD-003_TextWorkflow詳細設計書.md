---
title: "TextWorkflow詳細設計書"
file_name: "CLW-DD-003_TextWorkflow詳細設計書.md"
document_type: "detailed_design"
version: "1.0"
created_at: "2026-08-31"
updated_at: "2026-08-31"
author: "未記載"
purpose: "TextWorkflowの入力・出力DTO、処理パイプライン、設定境界、失敗契約を定義するため"
related_documents:
  - "CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md"
  - "../how-to/HOWTO_TEXT_WORKFLOW_RULES.md"
---

# 詳細設計書（TextWorkflow）
**テキスト分類、テンプレート展開、正規化、実行履歴の制御仕様**

| 項目           | 内容                                 |
| :------------- | :----------------------------------- |
| 文書番号       | CLW-DD-003                           |
| ファイル名     | CLW-DD-003_TextWorkflow詳細設計書.md |
| ドキュメント名 | TextWorkflow詳細設計書               |
| 版数           | Rev.1.0                              |
| 改訂日         | 2026-08-31                           |
| 作成日         | 2026-08-31                           |
| 作成者         | 未記載                               |

---

## 1. 概要とSSOT境界

本設計書は、Clip_Watcher 内でクリップボードテキストまたは明示入力テキストを構造的に分類し、テンプレート展開・テキスト正規化を行い、その結果と実行履歴を安全に記録・返却する Python 製テキスト処理基盤 (`TextWorkflow`) の仕様・設計を定義する。

外部ツールへの依存を排し、Python の標準ライブラリおよび Clip_Watcher の既存コンポーネント (`ApplicationBuilder`, `EventDispatcher`, `HistoryService`) と柔軟かつ安全に接続可能なモジュール群として設計する。

### 1.1 スコープ

- **テキスト分類 (Classifier)**: ルール (正規表現、キーワード、テキスト長等) による自動カテゴリ判定。
- **テンプレート展開 (TemplateRenderer)**: 安全な変数埋め込み (`{{input}}`, `{{date}}` 等) による動的テキスト生成。
- **テキスト正規化 (Normalizer)**: 改行コード統一、末尾空白トリム、Unicode正規化等の前処理・後処理。
- **設定レイヤー合成 (ConfigurationResolver)**: 組み込み・ユーザー設定・ワークスペース設定・実行時オーバーライドの階層マージ。
- **専用実行履歴 (ExecutionHistory)**: 既存のクリップボード履歴とは独立した Workflow 実行結果の保存。
- **Clip_Watcher 統合**: GUI/イベント駆動による非同期実行 seam の提供。

### 1.2 非スコープ
- クライアント・サーバー間通信やクラウド同期機能。
- 任意の Python コード/シェルコマンドの動的評価・実行。

---

## 2. アーキテクチャ (Architecture)

```mermaid
graph TD
    GUI[GUI / Clipboard Monitor] -->|WorkflowRequest| WS[TextWorkflowService]
    CLI[CLI Runner] -->|WorkflowRequest| WS

    subgraph "TextWorkflow Core (src/core/text_workflow/)"
        WS --> TW[TextWorkflow Manager]
        CR[ConfigurationResolver] --> TW
        TW --> CF[Classifier]
        TW --> TR[TemplateRenderer]
        TW --> NM[Normalizer]
        TW --> EH[ExecutionHistory]
    end

    CF --> Rules[rules.json]
    TR --> Templates[templates.json]
    EH --> DB[(Local SQLite / Private Store)]

    TW -->|WorkflowResult| WS
    WS -->|Event / Callback| GUI
```

`TextWorkflow` は分類・展開・正規化・履歴記録の順序制御と失敗分離をカプセル化するディープモジュールとする。呼び出し側は単一の `WorkflowRequest` を渡し、`WorkflowResult` を受け取るのみで完結する。

---

## 3. インターフェースとDTO仕様

TextWorkflowは、分類・展開・正規化・履歴記録の順序制御と失敗分離をカプセル化するディープモジュールです。呼び出し側は次の入力DTOを渡し、出力DTOを受け取ります。

### 3.1 列挙値と分類DTO

| DTO / 列挙        | フィールドまたは値                                             | 型            | 制約・意味                                     |
| :---------------- | :------------------------------------------------------------- | :------------ | :--------------------------------------------- |
| `SourceKind`      | `EXPLICIT_TEXT` / `CLIPBOARD`                                  | enum          | 入力元が明示テキストかクリップボードかを表す。 |
| `ExecutionStatus` | `COMPLETED` / `COMPLETED_WITH_WARNING` / `REJECTED` / `FAILED` | enum          | 実行の終端状態を表す。                         |
| `Classification`  | `category_id`                                                  | string        | 分類されたカテゴリ識別子。                     |
| `Classification`  | `matched_rule_id`                                              | string / null | 適用されたルールの識別子。                     |
| `Classification`  | `confidence`                                                   | number        | 分類確度。既定値は `1.0`。                     |
| `Classification`  | `tags`                                                         | string[]      | 分類に付与するタグ。                           |

### 3.2 入力DTO: `WorkflowRequest`

| フィールド              | 型            | 必須  | 既定値 | 制約・意味                             |
| :---------------------- | :------------ | :---: | :----- | :------------------------------------- |
| `request_id`            | string        | 必須  | —      | 呼び出しを一意に識別する。             |
| `source_kind`           | `SourceKind`  | 必須  | —      | 入力元の種別。                         |
| `input_text`            | string        | 必須  | —      | 処理対象テキスト。入力上限は§6に従う。 |
| `workspace_root`        | string / null | 任意  | null   | ワークスペース設定を解決する基準位置。 |
| `category_hint`         | string / null | 任意  | null   | 分類結果を補助するカテゴリ指定。       |
| `template_id`           | string / null | 任意  | null   | 使用するテンプレートの指定。           |
| `normalization_profile` | string / null | 任意  | null   | 適用する正規化プロファイル。           |
| `save_history`          | boolean       | 任意  | true   | 実行履歴を保存するかを表す。           |
| `runtime_overrides`     | object        | 任意  | `{}`   | 呼び出し単位の設定上書き。             |

### 3.3 出力DTO: `WorkflowResult`

| フィールド            | 型                      | 必須  | 制約・意味                |
| :-------------------- | :---------------------- | :---: | :------------------------ |
| `request_id`          | string                  | 必須  | 対応する入力DTOの識別子。 |
| `status`              | `ExecutionStatus`       | 必須  | 実行の終端状態。          |
| `output_text`         | string / null           | 任意  | 変換後のテキスト。        |
| `classification`      | `Classification` / null | 任意  | 分類結果。                |
| `applied_template_id` | string / null           | 任意  | 適用したテンプレート。    |
| `applied_normalizers` | string[]                | 任意  | 実行した正規化処理。      |
| `warnings`            | string[]                | 任意  | 処理継続可能な警告。      |
| `error_message`       | string / null           | 任意  | 失敗または拒否の説明。    |

---

## 4. 各コンポーネントの仕様

### 4.1 ConfigurationResolver (`src/core/text_workflow/config_resolver.py`)
設定を以下の優先度順にディープマージする (右側優先)。
`Built-in Defaults` → `User Config (アプリ設定ディレクトリ配下の workflow.json)` → `Workspace Config (.clipwatcher/workflow.json)` → `Runtime Overrides`

アプリ設定ディレクトリは [CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md](CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md) §8「データ永続化 (SQLite & JSON)」の永続化方針を正本とし、Windowsでは `%USERPROFILE%\.clipWatcher\`、その他のOSでは `~/.clipwatcher/` を指す。

### 4.2 Classifier (`src/core/text_workflow/classifier.py`)
- 分類ルールは `rules.json` の `rules` 配列で定義する。各ルールは次の項目を持つ。

| 項目         | 型            | 必須  | 説明                                                                                  |
| :----------- | :------------ | :---: | :------------------------------------------------------------------------------------ |
| `id`         | string        | 必須  | ルールを一意に識別する。                                                              |
| `priority`   | integer       | 必須  | 小さい値を優先し、同値の場合は `rule_id` 昇順で評価する。                             |
| `categoryId` | string        | 必須  | マッチ時に割り当てるカテゴリ。                                                        |
| `templateId` | string / null | 任意  | 適用するテンプレート。                                                                |
| `when`       | object        | 必須  | `all`、`any`、`not` と `contains`、`containsAny`、`regex`、文字数条件を組み合わせる。 |

利用者向けの設定例と条件の詳細は [Text Workflow 分類ルールの作成・設定ガイド](../how-to/HOWTO_TEXT_WORKFLOW_RULES.md) を参照する。

### 4.3 TemplateRenderer (`src/core/text_workflow/template_renderer.py`)
- Python の標準文字列置換または軽量安全テンプレエンジンを利用。
- 許可する変数: `{{input}}`, `{{date}}`, `{{category}}`, `{{tags}}` および明示的に指定されたカスタム変数。
- 任意コード実行 (`eval`, `exec`) や環境変数への任意アクセスは遮断。

### 4.4 Normalizer (`src/core/text_workflow/normalizer.py`)
- 定義済みプロファイルに従い、冪等性 (`normalize(normalize(x)) == normalize(x)`) を保ってテキストを整形。
- 提供プロファイル例:
  - `normalize-newlines`: CR/LF を LF に統一。
  - `trim-trailing-space`: 各行末尾の空白を削除。
  - `ensure-final-newline`: ファイル末尾に改行を付与。
  - `unicode-nfc`: Unicode 正規化 (NFC)。

### 4.5 ExecutionHistory (`src/core/text_workflow/history.py`)
- 既存のクリップボード履歴 DB とは独立した専用テーブル (`t_workflow_history`) または SQLite ファイルに結果を記録。
- 保持上限数 (例: 直近 500 件) や有効期限による自動パージ機能をサポート。

---

## 5. Clip_Watcher との統合方針 (Integration Plan)

### 5.1 モジュール配置案

```text
src/
  core/
    text_workflow/
      __init__.py
      workflow.py          # メインコントローラー TextWorkflow
      classifier.py        # ルール判定 Classifier
      template_renderer.py # テンプレート展開
      normalizer.py        # テキスト正規化
      config_resolver.py   # 設定マージ
      history.py           # 専用履歴管理
  services/
    text_workflow_service.py # 依存注入用サービスラッパー
```

### 5.2 ApplicationBuilder への登録
`ApplicationBuilder.with_text_workflow_service(master, app_data_dir)` で `TextWorkflowService` を初期化し、`MainApplication.text_workflow_service` として GUI / コマンドハンドラに注入する（`with_event_dispatcher()` の後に呼び出す必要がある）。

`ConfigurationResolver` は `ConfigurationResolver.from_app_data_dir(app_data_dir)` で構築し、`app_data_dir` 配下の `workflow.json`（ユーザー設定）を実ファイルから読み込む。ワークスペース設定は構築時ではなく、`WorkflowRequest.workspace_root` が指定された場合に `resolve()` 呼び出しごとに `{workspace_root}/.clipwatcher/workflow.json` から動的に読み込まれる。設定ファイルが存在しない、または読み込みに失敗した場合は組み込み既定値にフォールバックし、アプリ起動を止めない（§7 の安全な失敗方針）。

`ExecutionHistory` は `app_data_dir` 配下の `text_workflow_history.db`（クリップボード履歴とは独立した専用SQLiteファイル）を使用する。

### 5.3 スレッド・非同期実行
テキスト処理および履歴記録は GUI メインスレッドをブロックしないよう、`TextWorkflowService` が `concurrent.futures.ThreadPoolExecutor` で非同期実行する。

実行結果の通知は次の経路をとる。

1. ワーカースレッド上で `TextWorkflow.execute()` が完了する。
2. `TextWorkflowService` に注入された `ui_thread_marshal`（Production では `lambda fn: master.after(0, fn)`）を介して、通知処理を Tkinter メインスレッドへ引き渡す。
3. メインスレッド上で `EventDispatcher.dispatch("TEXT_WORKFLOW_RESULT", result)` を実行し、購読側（GUI）へ `WorkflowResult` を通知する。

`ui_thread_marshal` を指定しない場合（GUIを持たないテスト・CLI用途）は、通知はワーカースレッドから直接行われる。GUIと統合する場合は必ず `ui_thread_marshal` を指定し、Tkinter APIをワーカースレッドから直接呼び出さないこと。

---

## 6. 公開Interfaceと互換性ポリシー

TextWorkflow は `src/core/text_workflow/__init__.py` の `__all__` に列挙するシンボルのみを公開 Interface とする。それ以外のサブモジュール（`classifier.py`, `normalizer.py`, `template_renderer.py` 等）は内部実装であり、事前告知なく変更・削除しうる。

### 6.1 公開シンボル（Public API）

| シンボル            | 種別     | 変更方針                                                                 |
| :------------------ | :------- | :----------------------------------------------------------------------- |
| `TextWorkflow`      | クラス   | `execute(request) -> WorkflowResult` のシグネチャを破壊的変更しない。    |
| `WorkflowRequest`   | DTO      | 既存フィールドの削除・型変更をしない。追加は既定値付きの任意項目とする。 |
| `WorkflowResult`    | DTO      | 同上。                                                                   |
| `SourceKind`        | enum     | 既存メンバーを削除しない。                                               |
| `ExecutionStatus`   | enum     | 同上。                                                                   |
| `Classification`    | DTO      | 既存フィールドの削除・型変更をしない。                                   |
| `TextWorkflowError` | 例外基底 | TextWorkflow パッケージ内で発生する例外はこれを継承する（§6.3参照）。    |

呼び出し側は `from src.core.text_workflow import TextWorkflow, WorkflowRequest, WorkflowResult, ...` の形でのみ import する。サブモジュールへの直接 import（例: `from src.core.text_workflow.classifier import Classifier`）は内部実装への依存であり、互換性を保証しない。

### 6.2 拡張点（Extension Points）

以下は「利用可能だが互換性ポリシーは公開Interfaceより緩い」拡張点として位置づける。DI（依存性注入）や独自実装の差し替えを目的として `TextWorkflow.__init__()` の引数として利用することを想定する。

| シンボル                | 配置                                        | 位置づけ                                                                                                 |
| :---------------------- | :------------------------------------------ | :------------------------------------------------------------------------------------------------------- |
| `ConfigurationResolver` | `src/core/text_workflow/config_resolver.py` | `TextWorkflow(config_resolver=...)` で注入可能。コンストラクタ引数・`resolve()` の戻り値構造は維持する。 |
| `ExecutionHistory`      | `src/core/text_workflow/history.py`         | `TextWorkflow(history=...)` で注入可能。`record()`/`get_recent()` のシグネチャは維持する。               |
| `HistoryEntry`          | `src/core/text_workflow/history.py`         | `ExecutionHistory` とセットで利用するDTO。                                                               |
| `TextWorkflowService`   | `src/services/text_workflow_service.py`     | GUI/イベント駆動からの非同期呼び出し窓口。                                                               |

拡張点は破壊的変更の際に改訂履歴への記載を必須とするが、公開Interfaceほどの後方互換保証（同一メジャーバージョン内での維持）は課さない。

### 6.3 例外方針

TextWorkflow は **Result パターン**を採用し、`TextWorkflow.execute()` は原則として例外を発生させず、失敗時は `WorkflowResult(status=REJECTED または FAILED, error_message=...)` を返す。

- 内部コンポーネント（`Classifier`, `TemplateRenderer`, `Normalizer` 等）が発生させる例外は、`TextWorkflowError`（`src/core/text_workflow/errors.py`）を継承するものに限定する。
- `TextWorkflow.execute()` は内部で `TextWorkflowError` を捕捉し、`WorkflowResult` へ変換して返す。呼び出し側が `TextWorkflowError` を直接捕捉する必要はない。
- `TextWorkflowError` を継承しない例外（`sqlite3.Error` 等の外部ライブラリ例外、未分類の `Exception`）が内部コンポーネントから伝播した場合は実装上の不備であり、修正対象とする。

### 6.4 非公開（内部実装）

`Classifier`, `Normalizer`, `TemplateRenderer`, `TemplateError`, `NORMALIZERS`, `DEFAULT_PROFILES`, `deep_overlay`, `DEFAULT_BUILTIN_CONFIG` は実装の詳細であり、公開Interfaceの一部ではない。テストコードからの直接importは許容するが、外部呼び出し元（GUI・イベントハンドラ・将来の別配布物）からの依存は避ける。

---

## 7. エラーハンドリング & セキュリティ

- **入力サイズ制限**: デフォルトで 1MB 以上のテキストはパース前に拒否 (`INPUT_TOO_LARGE`)。
- **ReDoS 対策**: 分類用の正規表現には次の制限を適用する。
  - パターン長は既定で200文字までとする。上限超過または構文エラーのパターンはマッチなしとして扱い、分類を継続する。
  - 評価はWindows互換の `multiprocessing` 子プロセス（`spawn`）に隔離し、既定0.5秒以内に完了しない場合は `terminate()` で子プロセスを強制終了してマッチなしとして扱う。これにより、CPython標準 `re` のバックトラックが呼び出し元・GUIスレッドをブロックしないことを保証する。
  - 制限値は設定の `workflow.classifierRegexMaxPatternLength` と `workflow.classifierRegexTimeoutSeconds` で上書き可能とする。プロセス生成のオーバーヘッドがあるため、`regex` ルールは必要最小限にする。
- **安全な失敗 (Graceful Degradation)**: 履歴書き込みが失敗しても、変換されたテキスト出力自体は壊さず `COMPLETED_WITH_WARNING` として結果を返却。正規表現の拒否・タイムアウト時も、該当ルールを非マッチとして後続ルールまたは既定カテゴリで処理を継続する。

---

## 8. テスト計画 (Testing Strategy)

- **単体テスト (`tests/unit/test_text_workflow.py`)**:
  - `ConfigurationResolver` の層別優先マージテスト
  - `Classifier` のルール順序・条件判定テスト
  - ReDoS対策（パターン長超過の拒否、破滅的バックトラック時の子プロセス終了、通常パターンの回帰）
  - `TemplateRenderer` の変数置換・未定義変数テスト
  - `Normalizer` の冪等性検証
- **統合テスト (`tests/integration/test_workflow_pipeline.py`)**:
  - リクエスト受信から分類・展開・正規化・履歴記録までのパイプライン一連動作のテスト


## 9. 改訂履歴

| 版数    | 改訂日     | 変更者 | 変更内容・変更理由 (Why)                                                                                                                                                                                                          |
| :------ | :--------- | :----- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rev.1.0 | 2026-08-31 | 未記載 | Text Workflow設計書を詳細設計書として命名・分類し、DTOとルール定義を表形式へ置換、how-toへの参照と改訂履歴を整備。                                                                                                                |
| Rev.1.1 | 2026-09-01 | 未記載 | §4.1の設定保存先を `~/.clip_watcher/` から BD-001 §8 と実装（`.clipWatcher`/`.clipwatcher`）に一致する記述へ修正。                                                                                                                |
| Rev.1.2 | 2026-09-01 | 未記載 | §6として公開Interface・拡張点・例外方針・互換性ポリシーを新設（旧§6・7は§7・8へ繰り下げ）。`TextWorkflowError` を実装に追加。                                                                                                     |
| Rev.1.3 | 2026-09-01 | 未記載 | §5.2/5.3を実装に合わせて更新。`ConfigurationResolver.from_app_data_dir()` による実ファイル読み込み、`ApplicationBuilder.with_text_workflow_service()` によるDI登録、`ui_thread_marshal` 経由の `EventDispatcher` 通知経路を反映。 |
| Rev.1.4 | 2026-09-01 | 未記載 | §7のReDoS対策を実装に合わせて詳細化。パターン長制限と、Windows互換の子プロセス隔離・強制終了による正規表現実行時間制限を定義。                                                                                                    |
