# ClipWatcher コア層プログラム仕様書

本書は、`src/core/` ディレクトリ配下に分割されたコアモジュール群の責務と、それらがどのように連携してアプリケーションを起動・制御しているか（プログラムフロー）を解説する技術仕様書です。

## 1. コア層のモジュール構成

コア層は、関心の分離（Separation of Concerns）に基づき、以下のサブパッケージに分割されています。

| サブパッケージ | 主な役割と構成クラス |
| :--- | :--- |
| `bootstrap/` | **起動と依存関係の構築**<br>・`ApplicationBuilder`: 各サービス・UIを生成し依存性を注入（DI）する。<br>・`BaseApplication`: アプリケーションの基底インターフェース。<br>・`DependencyChecker`: 起動前の環境・依存ライブラリのチェック。 |
| `clipboard/` | **OSクリップボード監視**<br>・`ClipboardMonitor`: OSのクリップボード変更を常時監視し、変更検知時にイベントを発行する。 |
| `events/` | **イベント駆動と状態遷移**<br>・`EventDispatcher`: Pub/Subモデルによるコンポーネント間通信のハブ。<br>・`commands.py`: Undo/Redo機能のためのコマンドパターン実装（`UpdateHistoryCommand`等）。 |
| `config/` | **設定管理と状態**<br>・`SettingsManager`: `settings.json` の読み書き。<br>・`AppStatus`: アプリ全体の状態保持。 |
| `app_main.py` | `BaseApplication` を実装する具象クラス。ビルドされたシステムを統括する。 |

---

## 2. アプリケーション起動フロー (Bootstrap Flow)

アプリケーションの起動は、エントリーポイント (`clip_watcher.py`) から `start_app()` 関数を介して開始され、`ApplicationBuilder` によって段階的に構築されます。

```mermaid
sequenceDiagram
    participant Main as clip_watcher.py
    participant Start as src/event_handlers/__init__.py<br>(start_app)
    participant Builder as ApplicationBuilder
    participant Core as 各種コア/サービス層
    participant GUI as ClipWatcherGUI
    participant App as MainApplication

    Main->>Start: start_app() 呼び出し
    Start->>Builder: ApplicationBuilder() インスタンス化
    
    Builder->>Builder: 1. 依存ライブラリチェック (DependencyChecker)
    Builder->>Core: 2. 基本サービス初期化 (EventDispatcher, SettingsManager)
    Builder->>Core: 3. DB & サービス層初期化 (DatabaseManager, HistoryService...)
    Builder->>Core: 4. モニター初期化 (ClipboardMonitor)
    Builder->>Builder: 5. イベントハンドラ登録 (History/File/Settings...)
    
    Builder->>GUI: 6. GUI構築 (ClipWatcherGUI)
    Builder->>Builder: 7. プラグイン読み込み (PluginManager)
    
    Builder->>App: build() 完了 (MainApplication 返却)
    Start->>App: run() 呼び出し
    App->>Core: ClipboardMonitor.start() (監視スレッド開始)
    App->>GUI: mainloop() (Tkinterイベントループ開始)
```

**【起動時のポイント】**
- **DI (依存性注入)**: サービスやハンドラは互いに直接インスタンス化せず、`ApplicationBuilder` が必要なオブジェクト（`EventDispatcher` など）をコンストラクタ経由で渡します。これにより循環参照を防いでいます。

---

## 3. クリップボード監視フロー (Monitoring Flow)

バックグラウンドで動作する `ClipboardMonitor` がクリップボードの変更を検知し、それが GUI に反映されるまでのフローです。

```mermaid
sequenceDiagram
    participant OS as OS Clipboard
    participant Monitor as ClipboardMonitor (別スレッド)
    participant DB as HistoryService / DAO
    participant Dispatcher as EventDispatcher
    participant App as MainApplication
    participant GUI as HistoryListComponent

    loop 0.5秒間隔
        Monitor->>OS: _check_clipboard()
        alt 変更あり
            Monitor->>Monitor: 除外アプリ判定
            Monitor->>DB: add_history_item(テキスト)
            DB-->>Monitor: 完了
            Monitor->>Dispatcher: dispatch("CLIPBOARD_CHANGED", テキスト)
        end
    end
    
    Dispatcher->>App: イベント通知
    App->>GUI: update_clipboard_display() 呼び出し
    GUI->>DB: 最新の履歴リストを取得
    GUI->>GUI: リストボックスの描画更新
```

**【監視フローのポイント】**
- `ClipboardMonitor` は別スレッドで稼働しますが、直接 GUI を操作しません。`EventDispatcher` を介してイベントを発行することで、Tkinterのメインスレッド（`MainApplication` 側）で安全に描画更新が行われます。

---

## 4. イベント・コマンド制御フロー (Control Flow)

ユーザーが GUI からアクションを起こした際のフローです（例：履歴のフォーマット適用や編集）。

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant GUI as ContextMenu / Dialog
    participant Handlers as HistoryEventHandlers
    participant Undo as UndoManager
    participant Cmd as UpdateHistoryCommand
    participant DB as HistoryService

    User->>GUI: 履歴の編集・フォーマット操作
    GUI->>Handlers: dispatch("HISTORY_ITEM_EDITED", データ)
    
    Handlers->>Cmd: UpdateHistoryCommand(対象ID, 新テキスト) 生成
    Handlers->>Undo: execute_command(Cmd)
    
    Undo->>Cmd: execute()
    Cmd->>DB: update_history_item_by_id() (DB更新)
    Cmd->>App: GUI更新要求
```

**【制御フローのポイント】**
- 操作はすべて `src/event_handlers/` 内のハンドラで受け止めます。
- 状態を変更する操作（更新、削除など）は `src/core/events/commands.py` に定義されたコマンドオブジェクトにカプセル化されます。これにより、将来的に `undo()` メソッドを呼ぶだけでデータベースと GUI の状態を元に戻すことができます。
