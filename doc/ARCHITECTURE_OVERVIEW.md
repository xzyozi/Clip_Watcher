# ClipWatcher アーキテクチャ概要

このドキュメントは、ClipWatcherアプリケーションの主要なコンポーネント、イベント駆動の仕組み、およびクラス間の関連性についての概要を説明します。

## 1. 全体的なアーキテクチャ

アプリケーションは、関心の分離を目的として、主に以下のディレクトリに分割されています。

-   `src/core`: ビジネスロジック、状態管理など、アプリケーションの中核をなす機能。
-   `src/gui`: ユーザーインターフェース（UI）に関連するすべてのクラス。
-   `src/event_handlers`: UIからのアクションを`core`のロジックに結びつけるためのイベントハンドラ。
-   `src/plugins`: クリップボードの内容を変換するためのプラグイン。
-   `src/utils`: ログ設定やエラーハンドリングなど、アプリケーション全体で共有されるユーティリティ。

`clip_watcher.py` の `Application` クラスが全体を統括し、`ApplicationBuilder` が各コンポーネントを組み立ててアプリケーションを構築します。

## 2. データフローの例

クリップボードの変更がUIに反映されるまでの基本的なデータフローは以下の通りです。

```
OSクリップボード -> [ClipboardMonitor] --(監視)--> [EventDispatcher] --("CLIPBOARD_CHANGED" イベント)--> [Application] -> [ClipWatcherGUI] -> [HistoryListComponent]
```

1.  `ClipboardMonitor` がOSのクリップボードの変更を検知します。
2.  `EventDispatcher` を通じて `CLIPBOARD_CHANGED` イベントを発行します。
3.  `Application` クラスがイベントを受け取り、`ClipWatcherGUI` の表示更新メソッドを呼び出します。
4.  `ClipWatcherGUI` が `HistoryListComponent` などの関連コンポーネントの表示を更新します。

## 3. Core コンポーネント

`src/core` ディレクトリには、アプリケーションの心臓部となるクラスが含まれています。

| クラス | 説明 |
| :--- | :--- |
| `Application` | すべてのコンポーネントを保持し、全体を統括するメインクラス。 |
| `ApplicationBuilder` | `Application` のインスタンスを生成するために、必要なコンポーネントを順に組み立てるビルダークラス。 |
| `EventDispatcher` | Pub/Sub パターンを実装し、コンポーネント間の疎結合な通信を実現するイベントバス。 |
| `ClipboardMonitor` | OSのクリップボードを監視し、変更があった場合に `CLIPBOARD_CHANGED` イベントを発行する。 |
| `SettingsManager` | `settings.json` の読み込み、保存、および設定変更時の `SETTINGS_CHANGED` イベントの発行を管理する。 |
| `ThemeManager` | アプリケーションのテーマ（ライト/ダーク）を管理し、`ttk` スタイルと `tk` ウィジェットのスタイルを動的に適用する。 |
| `UndoManager` | コマンドパターンを利用して、元に戻す（Undo）/やり直し（Redo）の操作を管理する。 |
| `PluginManager` | `src/plugins` ディレクトリからプラグインを動的に読み込み、管理する。 |
| `FixedPhrasesManager` | 定型文のデータを管理する。 |

## 4. GUI レイヤー

`src/gui` ディレクトリは、ユーザーが見て操作するすべての要素を含みます。

-   **`ClipWatcherGUI`**: メインウィンドウそのもの。クリップボードタブと定型文タブを持つノートブックを含む。
-   **`components/`**: `HistoryListComponent` や `PhraseListComponent` など、メインウィンドウ内で再利用されるUI部品。
-   **`BaseToplevelGUI`**: `SettingsWindow` や `QuickTaskDialog` などのすべてのポップアップウィンドウの基底クラス。テーマと「常に手前に表示」設定の継承を保証する。
-   **`BaseContextMenu` とそのサブクラス**: 右クリックメニューのロジックをカプセル化するクラス群。`HistoryContextMenu` や `TextWidgetContextMenu` など、対象ごとに特化したメニューを提供する。
-   **`ThemeManager`**: `config.py` に定義された配色に基づき、`ttk` ウィジェットのスタイルを一元的に設定し、標準の `tk` ウィジェット（`Menu`, `Text` など）にも再帰的にスタイルを適用する。

## 5. イベント駆動アーキテクチャ

コンポーネント間の通信は、`EventDispatcher` を介したイベントの送受信によって行われます。これにより、各コンポーネントは他のコンポーネントの実装を意識することなく、疎結合に保たれます。

### 主要なイベント

| イベント名 | ペイロード | 発行元 (例) | 購読者 (例) | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| `SETTINGS_CHANGED` | `dict` | `SettingsManager` | `Application` | 設定が変更されたことを通知する。 |
| `CLIPBOARD_CHANGED` | `str` | `ClipboardMonitor` | `Application` | クリップボードの内容が変更されたことを通知する。 |
| `HISTORY_COPY_SELECTED` | `tuple` | `ClipWatcherGUI`, `ContextMenu` | `HistoryEventHandlers` | 選択された履歴項目のコピーを要求する。 |
| `REQUEST_UNDO_LAST_ACTION` | `None` | `ClipWatcherGUI`, `ContextMenu` | `HistoryEventHandlers` | `UndoManager` を介して元に戻す操作をトリガーする。 |
| `SETTINGS_ALWAYS_ON_TOP` | `bool` | `MenuBar` | `SettingsEventHandlers` | 「常に手前に表示」設定の変更を要求する。 |

## 6. コマンドパターン (Undo/Redo)

元に戻す/やり直し機能は、コマンドパターンを用いて実装されています。

-   **`UpdateHistoryCommand`**: 履歴項目の編集やフォーマットなど、状態を変更する操作はすべてコマンドオブジェクトとしてカプセル化されます。
-   **`UndoManager`**: 実行されたコマンドオブジェクトをスタックに保持します。`undo()` が呼び出されると、最後のコマンドの `undo()` メソッドを実行して状態を元に戻します。

## 7. プラグインシステム

`src/plugins` ディレクトリ内の各プラグインは `BasePlugin` を継承し、`process` メソッドを実装します。`PluginManager` はこれらのプラグインを起動時に動的に読み込み、「フォーマット」機能などで利用可能にします。

## 8. データ永続化

ユーザーのデータと設定は、以下のJSONファイルとして永続化されます。

-   **場所**:
    -   Windows: `%APPDATA%\ClipWatcher\`
    -   Linux/macOS: `~/.clipwatcher/`
-   **ファイル**:
    -   `settings.json`: アプリケーションの全般的な設定。
    -   `history.json`: クリップボードの履歴。
    -   `fixed_phrases.json`: ユーザーが定義した定型文。
