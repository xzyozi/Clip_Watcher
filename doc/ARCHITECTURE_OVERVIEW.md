# ClipWatcher アーキテクチャ概要

このドキュメントは、ClipWatcherアプリケーションの主要なコンポーネント、イベント駆動の仕組み、およびクラス間の関連性についての概要を説明します。

## 1. 全体的なアーキテクチャ

アプリケーションは、関心の分離を目的として、主に以下のディレクトリに分割されています。

-   `src/core`: ビジネスロジック、状態管理など、アプリケーションの中核をなす機能。
-   `src/gui`: ユーザーインターフェース（UI）に関連するすべてのクラス。
-   `src/event_handlers`: UIからのアクションを`core`のロジックに結びつけるためのイベントハンドラ。
-   `src/plugins`: クリップボードの内容を変換したり、GUIツールを提供したりするためのプラグイン。
-   `src/utils`: ログ設定やエラーハンドリングなど、アプリケーション全体で共有されるユーティリティ。

`clip_watcher.py` の `MainApplication` クラスが全体を統括し、`ApplicationBuilder` が各コンポーネントを組み立ててアプリケーションを構築します。

## 2. データフローの例

クリップボードの変更がUIに反映されるまでの基本的なデータフローは以下の通りです。

```
OSクリップボード -> [ClipboardMonitor] --(監視)--> [EventDispatcher] --("CLIPBOARD_CHANGED" イベント)--> [MainApplication] -> [ClipWatcherGUI] -> [HistoryListComponent]
```

1.  `ClipboardMonitor` がOSのクリップボードの変更を検知します。
2.  `EventDispatcher` を通じて `CLIPBOARD_CHANGED` イベントを発行します。
3.  `MainApplication` クラスがイベントを受け取り、`ClipWatcherGUI` の表示更新メソッドを呼び出します。
4.  `ClipWatcherGUI` が `HistoryListComponent` などの関連コンポーネントの表示を更新します。

## 3. Core コンポーネント

`src/core` ディレクトリには、アプリケーションの心臓部となるクラスが含まれています。

| クラス | 説明 |
| :--- | :--- |
| `MainApplication` | すべてのコンポーネントを保持し、全体を統括するメインクラス。 |
| `ApplicationBuilder` | `MainApplication` のインスタンスを生成するために、必要なコンポーネントを順に組み立てるビルダークラス。 |
| `EventDispatcher` | Pub/Sub パターンを実装し、コンポーネント間の疎結合な通信を実現するイベントバス。 |
| `ClipboardMonitor` | OSのクリップボードを監視し、変更があった場合に `CLIPBOARD_CHANGED` イベントを発行する。 |
| `SettingsManager` | `settings.json` の読み込み、保存、および設定変更時の `SETTINGS_CHANGED` イベントの発行を管理する。 |
| `ThemeManager` | アプリケーションのテーマ（ライト/ダーク）を管理し、`ttk` スタイルと `tk` ウィジェットのスタイルを動的に適用する。 |
| `UndoManager` | コマンドパターンを利用して、元に戻す（Undo）/やり直し（Redo）の操作を管理する。 |
| `PluginManager` | `src/plugins` ディレクトリからプラグインを動的に読み込み、管理する。テキスト処理プラグインとGUIを持つツールプラグインの両方を扱う。 |
| `FixedPhrasesManager` | 定型文のデータを管理する。 |

## 4. GUI レイヤー

`src/gui` ディレクトリは、ユーザーが見て操作するすべての要素を含みます。

-   **`ClipWatcherGUI`**: メインウィンドウそのもの。クリップボードタブ、定型文タブ、そして**プラグインから動的に読み込まれるツールタブ**を持つノートブックを含む。
-   **`components/`**: `HistoryListComponent` や `PhraseListComponent` など、特定の機能に密接に関連し、アプリケーションのコア部分を構成する再利用可能なUI部品。
-   **`BaseToplevelGUI`**: `SettingsWindow` や `QuickTaskDialog` などのすべてのポップアップウィンドウの基底クラス。テーマと「常に手前に表示」設定の継承を保証する。
-   **`base/context_menu.py` とそのサブクラス**: 右クリックメニューのロジックをカプセル化するクラス群。`HistoryContextMenu` や `TextWidgetContextMenu` など、対象ごとに特化したメニューを提供する。
-   **`ThemeManager`**: `config.py` に定義された配色に基づき、`ttk` ウィジェットのスタイルを一元的に設定し、標準の `tk` ウィジェット（`Menu`, `Text` など）にも再帰的にスタイルを適用する。

## 5. イベント駆動アーキテクチャ

コンポーネント間の通信は、`EventDispatcher` を介したイベントの送受信によって行われます。これにより、各コンポーネントは他のコンポーネントの実装を意識することなく、疎結合に保たれます。

### 主要なイベント

| イベント名 | ペイロード | 発行元 (例) | 購読者 (例) | 説明 |
| :--- | :--- | :--- | :--- | :--- |
| `SETTINGS_CHANGED` | `dict` | `SettingsManager` | `MainApplication` | 設定が変更されたことを通知する。 |
| `CLIPBOARD_CHANGED` | `str` | `ClipboardMonitor` | `MainApplication` | クリップボードの内容が変更されたことを通知する。 |
| `HISTORY_COPY_SELECTED` | `tuple` | `ClipWatcherGUI`, `ContextMenu` | `HistoryEventHandlers` | 選択された履歴項目のコピーを要求する。 |
| `REQUEST_UNDO_LAST_ACTION` | `None` | `ClipWatcherGUI`, `ContextMenu` | `HistoryEventHandlers` | `UndoManager` を介して元に戻す操作をトリガーする。 |
| `SETTINGS_ALWAYS_ON_TOP` | `bool` | `MenuBar` | `SettingsEventHandlers` | 「常に手前に表示」設定の変更を要求する。 |

## 6. コマンドパターン (Undo/Redo)

元に戻す/やり直し機能は、コマンドパターンを用いて実装されています。

-   **`UpdateHistoryCommand`**: 履歴項目の編集やフォーマットなど、状態を変更する操作はすべてコマンドオブジェクトとしてカプセル化されます。
-   **`UndoManager`**: 実行されたコマンドオブジェクトをスタックに保持します。`undo()` が呼び出されると、最後のコマンドの `undo()` メソッドを実行して状態を元に戻します。

## 7. プラグインシステム (GUIツール統合)

アプリケーションの拡張性はプラグインシステムによって担保されます。`src/plugins` ディレクトリ内の各プラグインは `BasePlugin` を継承します。`PluginManager` はこれらのプラグインを起動時に動的に読み込みます。

プラグインには2つの主要なタイプがあります。

### 1. テキスト処理プラグイン
- クリップボードのテキストを操作・変換する機能を提供します。
- `process(text: str) -> str` メソッドを実装します。
- 「フォーマット」機能から利用されます。

### 2. GUIツールプラグイン
- アプリケーションに新しい機能タブを追加するための、自己完結したGUIコンポーネントを提供します。
- `BasePlugin` の以下のメソッドをオーバーライドします。
    - `has_gui_component() -> bool`: `True` を返すことで、GUIを持つプラグインであることを示します。
    - `create_gui_component(parent, app_instance) -> ttk.Frame`: `ttk.Notebook` を親として、タブ内に表示されるGUIコンポーネント（`ttk.Frame`を継承）を生成して返します。
- GUIコンポーネントのクラス定義は、プラグインファイル内に完全にカプセル化されており、外部のコンポーネントへの依存をなくしています。
- `main_gui.py` は `PluginManager` を通じてこれらのプラグインを検出し、`create_gui_component` を呼び出して動的にタブを生成・表示します。これにより、`main_gui.py` を変更することなく新しいツールをアプリケーションに追加できます。

## 8. データ永続化

ユーザーのデータと設定は、以下のOS標準のユーザーディレクトリ配下にJSONファイルとして永続化されます。

-   **保存場所**:
    -   Windows: `%USERPROFILE%\.clipWatcher\`
    -   Linux/macOS: `~/.clipwatcher/`
-   **ファイル**:
    -   `history.json`: クリップボードの履歴。
    -   `settings.json`: アプリケーションの全般的な設定。
    -   `fixed_phrases.json`: ユーザーが定義した定型文。