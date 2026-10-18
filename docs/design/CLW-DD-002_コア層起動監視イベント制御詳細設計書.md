---
title: "コア層起動監視イベント制御詳細設計書"
file_name: "CLW-DD-002_コア層起動監視イベント制御詳細設計書.md"
document_type: "detailed_design"
version: "1.5"
created_at: "2026-08-31"
updated_at: "2026-10-18"
author: "Antigravity"
purpose: "コア層の起動、クリップボード監視、イベント・コマンド制御の責務と連携契約を定義するため"
related_documents:
  - "CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md"
  - "CLW-BD-002_ClipWatcher機能基本設計書.md"
---

# 詳細設計書（コア層起動監視イベント制御）
**起動配線、監視フロー、イベント・コマンド制御の設計契約**

| 項目           | 内容                                               |
| :------------- | :------------------------------------------------- |
| 文書番号       | CLW-DD-002                                         |
| ファイル名     | CLW-DD-002_コア層起動監視イベント制御詳細設計書.md |
| ドキュメント名 | コア層起動監視イベント制御詳細設計書               |
| 版数           | Rev.1.5                                            |
| 改訂日         | 2026-10-18                                         |
| 作成日         | 2026-08-31                                         |
| 作成者         | Antigravity                                        |

---

## 1. 概要とSSOT境界

本書は、`src/core/` 配下のコアモジュール群がアプリケーションを起動・制御する際の責務と連携契約を定義します。全体の責務境界は [CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md](CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md) を正本とします。

## 2. コア層のモジュール構成

コア層は、関心の分離（Separation of Concerns）に基づき、以下のサブパッケージに分割されています。

| サブパッケージ | 主な役割と構成クラス                                                                                                                                                                                                                                                                                                                                                                                                     |
| :------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bootstrap/`   | **起動と依存関係の構築**<br>・`ApplicationBuilder`: 各サービス・UIを生成し依存性を注入（DI）する。<br>・`BaseApplication`: アプリケーションの基底インターフェース。<br>・`DependencyChecker`: 起動前の環境・依存ライブラリのチェック。                                                                                                                                                                                   |
| `clipboard/`   | **OSクリップボード監視**<br>・`ClipboardMonitor`: OSのクリップボード変更を常時監視し、変更検知時にイベントを発行する。                                                                                                                                                                                                                                                                                                   |
| `events/`      | **イベント駆動と状態遷移**<br>・`EventDispatcher`: Pub/Subモデルによるコンポーネント間通信のハブ。<br>・`commands.py`: Undo/Redo機能のためのコマンドパターン実装（`UpdateHistoryCommand`等）。                                                                                                                                                                                                                           |
| `config/`      | **設定管理と状態**<br>・`SettingsManager`: `settings.json` の読み書き。<br>・`AppStatus`: アプリ全体の状態保持。                                                                                                                                                                                                                                                                                                         |
| `platform/`    | **OS抽象化・アダプター**（詳細は§6）<br>・`protocols.py`: OS抽象インターフェース群（`ProcessInspector`, `SoundPlayer`, `SingleInstanceController`, `PasteSender`, `ClipboardReader`, `StartupController`, `HotkeyListener`等）。<br>・`services.py`: OS実装の選択を一元化する `PlatformServices`。<br>・`errors.py`: `PlatformError` / `UnsupportedFeatureError` / `SingleInstanceError`。<br>・`windows/` / `macos/` / `linux/` / `posix/`: 各OS向け具象アダプター。<br>・`null/`: 廃止完了（成功偽装の排除 #150, #161）。 |
| `app_main.py`  | `BaseApplication` を実装する具象クラス。ビルドされたシステムを統括する。                                                                                                                                                                                                                                                                                                                                                 |


---

## 3. アプリケーション起動フロー (Bootstrap Flow)

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

### 起動時のポイント

- **DI (依存性注入)**: サービスやハンドラは互いに直接インスタンス化せず、`ApplicationBuilder` が必要なオブジェクト（`EventDispatcher` など）をコンストラクタ経由で渡します。これにより循環参照を防いでいます。

---

## 4. クリップボード監視フロー (Monitoring Flow)

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

## 5. イベント・コマンド制御フロー (Control Flow)

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


## 6. プラットフォーム抽象レイヤー設計 (#158, #161)

OSごとに実装が異なる機能は `src/core/platform/` に隔離し、**どのOSでどの実装を使うかの選択は `PlatformServices` の1箇所**に集約します。各クラスが `sys.platform` で分岐して自前でアダプターを生成することは行いません。また、外部ライブラリを原則追加せずOS標準機能・APIを活用する「ゼロインストール原則」を維持します。

### 6.1 対象範囲

| 機能                       | Windows                                | macOS                                                          | Linux                                                          | 備考                                                                                                              |
| :------------------------- | :------------------------------------- | :------------------------------------------------------------- | :------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------- |
| `ProcessInspector`         | `WindowsProcessInspector`              | `MacOSProcessInspector` (`ctypes` AppKit / `osascript`)        | `LinuxProcessInspector` (`xprop` / `comm` / `WM_CLASS`)        | 最前面プロセスの実行ファイル名取得。macOSはアクセシビリティ権限不要なAppKit優先。                                 |
| `SoundPlayer`              | `WindowsSoundPlayer` (`winsound`)      | `MacOSSoundPlayer` (`/usr/bin/afplay`)                         | `LinuxSoundPlayer` (`paplay` / `canberra-gtk-play` 等)         | コピー通知音再生。非ブロッキング非同期実行。                                                                      |
| `SingleInstanceController` | `WindowsSingleInstanceController`      | `PosixSingleInstanceController` (`fcntl.flock`)                | `PosixSingleInstanceController` (`fcntl.flock`)                | 二重起動防止。POSIX共通でロックファイルによる非ブロッキング排他制御。                                              |
| `PasteSender`              | `WindowsPasteSender` (`keybd_event`)   | `MacOSPasteSender` (`osascript` Cmd+V)                         | `LinuxPasteSender` (`xdotool` Ctrl+V)                          | 履歴選択時の自動貼り付けキーストローク送信。                                                                      |
| `ClipboardReader`          | `WindowsClipboardReader` (`pywin32`)   | `MacOSClipboardReader` (`/usr/bin/pbpaste` #170)               | 非対応（Tkinter標準フォールバック）                            | `clipboard_get()` 失敗時の代替テキスト読み取り。                                                                 |
| `StartupController`        | `WindowsStartupController` (HKCU Run)  | `MacOSStartupController` (LaunchAgents plist)                  | `LinuxStartupController` (XDG autostart desktop)               | システム起動/ログイン時の自動起動制御。バッチファイル脆弱性を根本解消 (#110, #155)。                              |
| `HotkeyListener`           | `WindowsHotkeyListener` (RegisterHotKey)| 非対応 (`UnsupportedFeatureError`)                             | 非対応 (`UnsupportedFeatureError`)                             | グローバルホットキー。`NullHotkeyListener` を全廃し、未対応環境では明示的に無効化・UI案内する (#150, #161)。      |

### 6.2 `PlatformServices` の契約

| 項目     | 仕様                                                                                                                                                         |
| :------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 生成     | コンストラクタで各アダプター（未対応は `None`）を受け取る。本番用は `PlatformServices.for_current_platform()` で生成する。生成は `start_app()` の1箇所のみ。 |
| 取得     | `process_inspector()` / `sound_player()` / `single_instance()` / `paste_sender()` / `clipboard_reader()` / `startup_controller()` のメソッドで取得する。    |
| ホットキー | `create_hotkey_listener(master, on_triggered)` ファクトリメソッドで生成する。Windows 以外では `UnsupportedFeatureError` を送出する。                         |
| 非対応時 | 対応するアダプターが無い場合、取得メソッドは `UnsupportedFeatureError` を送出する。`None` や成功を装うNull実装は返さない。                                   |
| 不変性   | 生成後にアダプターを差し替えない。テストではコンストラクタにモックを渡す（`sys.platform` の差し替えは使わない）。                                            |

### 6.3 例外階層

| 例外                      | 基底               | 用途                                                                                                   |
| :------------------------ | :----------------- | :----------------------------------------------------------------------------------------------------- |
| `PlatformError`           | `ClipWatcherError` | プラットフォーム層の共通親。                                                                           |
| `UnsupportedFeatureError` | `PlatformError`    | 非対応の機能を要求した。`feature`（例: `"sound_player"`）と `platform`（`sys.platform`）を属性に持つ。 |
| `SingleInstanceError`     | `PlatformError`    | 排他ロック取得APIの失敗（`CreateMutexW` や `fcntl.flock` の失敗など）。重複起動とは区別する。           |

### 6.4 注入経路

1. `start_app()` が `PlatformServices.for_current_platform()` を生成する。
2. `ApplicationBuilder(platform_services)` がコンストラクタで受け取って保持する。
3. ビルダーが `ClipboardMonitor` / `MainApplication` へ必須引数 `platform_services` として渡す。
4. `with_global_hotkey_listener()` では、`platform_services.create_hotkey_listener()` を試行し、`UnsupportedFeatureError` 送出時は `hotkey_listener = None`, `hotkey_registration_manager = None` として配線する（`sys.platform` 直分岐や Null 実装は廃止）。
5. 各クラスは使う場所で取得し、`UnsupportedFeatureError` を捕捉して明示的に縮退する。

### 6.5 非対応時の縮退仕様

「縮退」は呼び出し側が警告ログ等で明示して継続することを指し、例外の握りつぶしや成功の偽装は行いません。

| 機能                       | 呼び出し側            | 非対応時の動作                                                                                                                                                                       |
| :------------------------- | :-------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ProcessInspector`         | `ClipboardMonitor`    | 起動時に `WARNING` を1回出す。`excluded_apps` が設定されている場合は `ERROR` に格上げする。除外判定は行わず、履歴保存は継続する。                                                    |
| `SoundPlayer`              | `NotificationManager` | 再生をスキップし、`DEBUG` ログを出す。                                                                                                                                               |
| `PasteSender`              | `MainApplication`     | 「自動貼り付けは非対応。クリップボードには内容を設定済み」の `WARNING` を出して継続する。                                                                                            |
| `ClipboardReader`          | `ClipboardMonitor`    | tkinter の `clipboard_get()` が失敗した場合の代替経路。Windows・macOS 以外の非対応環境は `WARNING` を1回だけ出し、そのポーリングは `None` を返して次回を待つ。                       |
| `SingleInstanceController` | `start_app()`         | 多重起動を防止できない旨の `WARNING` を出して起動する。                                                                                                                              |
| `StartupController`        | `MainApplication`     | 起動時の同期処理で `WARNING` を出し、自動起動設定の変更処理をスキップする。                                                                                                          |
| `HotkeyListener`           | `SettingsWindow` / UI | 設定UIで「Windows限定」である旨を表示し、設定保存時のバリデーションで「このプラットフォームではサポートされていません」エラーを表示して不正登録を防止する。                           |

### 6.6 `SingleInstanceController.acquire()` の契約

| 結果                  | 意味                       | 呼び出し側の動作                                                                                    |
| :-------------------- | :------------------------- | :-------------------------------------------------------------------------------------------------- |
| `True`                | ロックを取得した。         | 通常起動する。                                                                                      |
| `False`               | 他のインスタンスが起動中。 | 「Already Running」を表示して終了する。                                                             |
| `SingleInstanceError` | ロック取得APIが失敗した。  | `start_app()` の `try` 内で捕捉し、エラーを表示してログに記録して終了する。重複起動として扱わない。 |

`release()` は未取得の状態で呼んでも何もしない（冪等）。POSIX実装（`PosixSingleInstanceController`）では `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)` を用い、ファイルディスクリプタを保持して二重起動を排他します。

### 6.6a `ClipboardReader` と `ClipboardMonitor` の責務 (#169, #170)

- `ClipboardReader.read_text() -> str | None` は、失敗時 `None`、テキスト形式が処理できない場合は空文字を返す。
  - Windows実装 `WindowsClipboardReader`: 生成時に `win32clipboard` / `pywintypes` を import し、未導入なら `ImportError` を送出。
  - macOS実装 `MacOSClipboardReader`: 標準コマンド `/usr/bin/pbpaste` を使用してクリップボードのテキストを読み取る（外部依存なしのゼロインストール実装、タイムアウト1.0秒）。
- `ClipboardMonitor` はクリップボードの監視・変更検知・書き込み（`update_clipboard`）に専念し、履歴操作は `HistoryService`、通知は `NotificationManager` を呼び出し側が直接参照する。

### 6.6b `StartupController` と自動起動セキュリティ (#110, #155)

旧実装で存在した、スタートアップフォルダへのバッチファイル（`ClipWatcher.bat`）配置によるパス埋め込み・展開起因のインジェクション脆弱性を根本解消しました。
- **Windows**: `winreg` を用い、ユーザーレジストリ（`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`）に引用符で囲んだ絶対実行パスを安全に登録・削除。旧 `ClipWatcher.bat` がスタートアップフォルダに残存している場合は自動検出して削除・クリーンアップ。
- **macOS**: `~/Library/LaunchAgents/com.clipwatcher.app.plist` を標準の `plistlib` で生成・削除。
- **Linux**: XDG autostart 仕様に準拠し、`~/.config/autostart/clipwatcher.desktop` を生成・削除。

### 6.7 依存方向と副作用分離 (#141)

- プラットフォーム具象アダプターは `platform/protocols.py` のみに依存し、サービス層やGUI層に依存しません。
- **設定ウィンドウにおける副作用の分離 (#141)**:
  `SettingsWindow._validate_pending_values()` では `parse_hotkey_string()` によるホットキーの構文解析のみを実施し、OSへのホットキー再登録（`reconfigure()`）は行いません。実際の再登録処理は、設定値が確定・保存された後に発行される `SETTINGS_CHANGED` イベントを契機として `MainApplication.on_settings_changed()` で実施します。これにより、キャンセル時や他の設定値検証エラー時にホットキーのみ先行して書き換わる不整合を完全に防止しています。

## 7. テスト・検証要件

- `ApplicationBuilder` による依存生成・注入と起動順序を確認する。
- 監視スレッドがGUIを直接操作せず、イベント経由で画面更新されることを確認する。
- 更新・削除などの状態変更がコマンド経由で実行され、Undo/Redo契約を維持することを確認する。
- `PlatformServices` が、対応するアダプターを返し、非対応時に `UnsupportedFeatureError`（`feature` / `platform` 属性付き）を送出することを、コンストラクタへのモック注入で確認する。
- `ClipboardMonitor` が、`ProcessInspector` 非対応時に `WARNING` を出し、`excluded_apps` 設定時は `ERROR` に格上げし、履歴保存を継続することを確認する。
- `NotificationManager` が `SoundPlayer` 非対応時に再生をスキップすることを確認する。
- `MainApplication` が `PasteSender` 非対応時に警告ログを出して継続することを確認する。
- `ClipboardMonitor` が、tkinter 失敗時に `ClipboardReader` へフォールバックし、非対応時は `WARNING` を1回だけ出して `None` を返すことを確認する。
- `WindowsClipboardReader` が、fakeモジュール注入で `pywin32` なしの環境でも検証でき、`pywin32` 未導入時に `ImportError` を送出することを確認する。
- `PosixSingleInstanceController` が、`fcntl.flock` を使用して排他ロックを取得し、重複起動を正しく検出することを確認する。
- `MacOSProcessInspector`, `LinuxProcessInspector`, `MacOSSoundPlayer`, `LinuxSoundPlayer`, `MacOSPasteSender`, `LinuxPasteSender` の単体テストを確認する。
- `StartupController` の各OS向け実装（レジストリ、plist、desktop）の登録・解除および旧バッチ削除を確認する。
- ホットキー非対応環境において `SettingsWindow` がエラーメッセージを出して不正入力を防止し、副作用が生じないこと（#141）を確認する。
- 上記は windows / ubuntu の両CIで通ること。

## 8. 改訂履歴

| 版数    | 改訂日     | 変更者      | 変更内容・変更理由 (Why)                                                                                                                                                                   |
| :------ | :--------- | :---------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rev.1.0 | 2026-08-31 | 未記載      | コア層プログラム仕様書を詳細設計書として命名・分類し、SSOT境界、メタデータ、検証要件、改訂履歴を整備。                                                                                     |
| Rev.1.1 | 2026-10-11 | Antigravity | OSプラットフォーム抽象レイヤー (`src/core/platform`) の追加に伴うモジュール構成の更新 (#148)。                                                                                             |
| Rev.1.2 | 2026-10-13 | 未記載      | `PlatformServices` への実装選択の集約、例外階層、注入経路、非対応時の縮退仕様、`acquire()` の契約を§6に追加し、テスト要件を更新 (#158)。                                                   |
| Rev.1.3 | 2026-10-15 | 未記載      | `ClipboardReader` の追加と `win32_available` の診断用途への限定、`ClipboardMonitor` の責務を監視に限定（履歴・通知の委譲を除去）、`QuickTaskDialog` の書き込み経路を §6.6a に追加 (#169)。 |
| Rev.1.4 | 2026-10-18 | Antigravity | macOS 向け `ClipboardReader` 実装（`MacOSClipboardReader` / `pbpaste`）の追加と実機検証要件の反映 (#170)。                                                    |
| Rev.1.5 | 2026-10-18 | Antigravity | macOS/Linux 向け各具象アダプター拡充、`PosixSingleInstanceController`、`StartupController`新設とWindowsレジストリ移行（#110, #155）、`NullHotkeyListener`全廃（#150）、ホットキー検証の副作用分離（#141）を反映 (#161)。 |

