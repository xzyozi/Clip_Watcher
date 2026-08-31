# 改造仕様書: 設定画面のスキーマ駆動化 と グローバルホットキー機能の追加

| 項目   | 内容                                                                                                                            |
| :----- | :------------------------------------------------------------------------------------------------------------------------------ |
| 作成日 | 2026年8月18日                                                                                                                   |
| 対象   | `src/gui/windows/settings_window.py`, `src/core/config/settings_manager.py`, `reusable_gui/`, `src/core/`（新設サブパッケージ） |

---

## 1. 目的と背景

### 1.1 目的
1. 現在手書きで実装されている `src/gui/windows/settings_window.py` を、
   スキーマ駆動（`SettingField` + 汎用レンダラー）方式に置き換える。
2. その基盤の上に、グローバルホットキー（デフォルト: `Ctrl+Shift+F`）による
   ウィンドウの「表示 ⇔ 最小化」トグル機能を追加する。
3. 将来のタスクバー最小化・トレイ格納などの追加状態を、既存コードへの
   変更を最小限にして組み込めるクラス設計にする。

### 1.2 背景・現状の課題
- `src/gui/windows/settings_window.py` は設定項目1つにつき
  「変数宣言 → ウィジェット生成 → 保存処理 → 復元処理」の4箇所を
  手動で同期する必要があり、項目追加時の記述量と不整合リスクが大きい。
- `reusable_gui/` 配下には、`SettingField` のリスト（スキーマ）のみから
  UIを動的生成する汎用実装（`reusable_gui/windows/settings_window.py`）が
  既に存在するが、アプリ側 (`src/`) からは未使用。
- ホットキー機能・ウィンドウ状態管理・システムトレイ常駐は、いずれも
  「OS依存の検知処理」と「アプリ内の状態遷移」という2層構造を持つ点で
  共通しており、今回はこの2層を明確に分離した設計とする。
- 標準ライブラリ（`tkinter`, `ctypes`, `threading`）のみで実装する方針。
  `pywin32` は既存依存（クリップボード監視のフォールバック用途）を
  超えて新たに使用しない。

---

## 2. スコープ

### 2.1 対応する変更
- `src/gui/windows/settings_window.py` を `reusable_gui/windows/settings_window.py`
  ベースの薄いサブクラスに置き換える。
- `src/core/config/settings_manager.py` の `get_settings_schema()` を、
  コア設定の唯一の定義（source of truth）とする。
- プラグイン由来の `Modules` タブを、`PluginSettingsSchemaProvider` による
  動的スキーマとして正式にスコープへ含める。
- `reusable_gui/core/config/schema.py` の `WidgetType` に
  `HOTKEY_CAPTURE` を追加する。
- 新設: `src/core/hotkey/` （グローバルホットキー検知・登録状態の管理）
- 新設: `src/core/window/` （ウィンドウ表示状態管理）
- `SettingsManager` のデフォルト設定に `global_hotkey_enabled`,
  `global_hotkey_combo`, `pinned_hotkey_bindings` を追加する。
- 表示/最小化キー（予約ID `1`）と、ピン留め履歴に割り当てる複数キー
  （ID `2` 以降）を、同じ登録集合として管理する。
- `ApplicationBuilder` / `MainApplication` へのライフサイクル組み込み。

### 2.2 対応しない変更（別スコープ）
- システムトレイ常駐の実際の実装（`WindowState` の拡張余地のみ確保）。
- 設定画面のUIデザイン刷新（レイアウト・配色は既存のまま踏襲）。
- 現在UI生成コードがコメントアウトされ、実運用で機能していない
  「設定画面タブの表示切替」 (`show_*_settings_tab`) の再有効化または削除。
  既存の設定値は後方互換のため保持するが、移行後のスキーマには含めず、
  新たなUIも提供しない。整理方針は将来別要件として決定する。

---

## 3. 設定画面のスキーマ駆動化 詳細仕様

### 3.1 現状構成と移行後構成の比較

| 項目               | 現状 (`src/gui/windows/settings_window.py`) | 移行後                                                                                                     |
| :----------------- | :------------------------------------------ | :--------------------------------------------------------------------------------------------------------- |
| 設定項目の定義場所 | `__init__` 内の `tk.Variable` 宣言に散在    | コア設定は `SettingsManager.get_settings_schema()`、プラグイン設定は `PluginSettingsSchemaProvider` に分離 |
| UI生成             | `_create_widgets()` に手書きgridレイアウト  | `reusable_gui` 側 `_render_field()` が `WidgetType` に応じて自動生成                                       |
| 保存処理           | `_save_settings_logic()` に手動列挙         | `_collect_values()` が合成済みスキーマを走査して自動収集                                                   |
| 復元処理           | `_update_ui_from_settings()` に手動列挙     | 合成済みスキーマの走査により自動復元                                                                       |
| Modulesタブ        | 個別の `tool_tab_vars` を手動構築           | GUIプラグイン一覧から `SettingField` を動的生成                                                            |
| クラス階層         | `BaseToplevelGUI` を直接継承                | `reusable_gui.windows.settings_window.SettingsWindow` を継承した薄いラッパー                               |

### 3.2 クラス設計

```mermaid
classDiagram
    class BaseSettingsManager {
        <<abstract>>
        +get_settings_schema() list~SettingField~
        +get_setting(key, default)
        +set_setting(key, value)
        +save_settings()
        +notify_listeners()
    }
    class SettingsManager {
        +get_settings_schema() list~SettingField~
    }
    class PluginSettingsSchemaProvider {
        -plugin_manager: PluginManager
        +get_fields() list~SettingField~
    }
    class ReusableSettingsWindow {
        "reusable_gui.windows.settings_window.SettingsWindow"
        -_schema: list~SettingField~
        -_vars: dict~str, tk.Variable~
        +_get_schema() list~SettingField~
        +_render_field(parent, field, row)
        +_collect_values()
        +_update_ui_from_settings()
    }
    class AppSettingsWindow {
        "src/gui/windows/settings_window.py (置き換え後)"
        +_get_schema() list~SettingField~
        +_validate_pending_values() bool
    }
    BaseSettingsManager <|-- SettingsManager
    ReusableSettingsWindow <|-- AppSettingsWindow
    AppSettingsWindow --> SettingsManager : core schema
    AppSettingsWindow --> PluginSettingsSchemaProvider : module schema
```

- `AppSettingsWindow` は `ReusableSettingsWindow` を継承する薄いクラスとし、
  テーマ適用・翻訳・スキーマ合成・保存前検証だけを担当する。
- `ReusableSettingsWindow` は、既存の直接
  `settings_manager.get_settings_schema()` 呼び出しを保護メソッド
  `_get_schema()` に置き換える。既定実装はコアスキーマを返し、
  `AppSettingsWindow` がコアスキーマとプラグインスキーマを合成する。
- `WidgetType.HOTKEY_CAPTURE` のレンダリングは `reusable_gui` 側に
  汎用実装として追加する。ホットキーの登録可否というアプリ固有処理は
  `AppSettingsWindow._validate_pending_values()` に閉じ込める。

### 3.3 Modulesタブのスキーマ合成

`SettingsManager` が `PluginManager` に依存してはならないため、
`get_settings_schema()` 内でプラグインを検索しない。代わりに
`src/plugins/settings_schema_provider.py` に
`PluginSettingsSchemaProvider` を新設する。

```python
class PluginSettingsSchemaProvider:
    def __init__(self, plugin_manager: PluginManager) -> None:
        self._plugin_manager = plugin_manager

    def get_fields(self) -> list[SettingField]:
        fields: list[SettingField] = []
        for plugin in self._plugin_manager.get_gui_plugins():
            setting_key = f"show_{plugin.name.lower().replace(' ', '_')}_tab"
            fields.append(
                SettingField(
                    key=setting_key,
                    label=f"Show {plugin.name} Tab",
                    widget_type=WidgetType.CHECKBUTTON,
                    tab="Modules",
                    group="Main Window Tabs",
                    default=True,
                )
            )
        return fields
```

`AppSettingsWindow._get_schema()` は以下のように合成する。

```python
return [
    *self.settings_manager.get_settings_schema(),
    *PluginSettingsSchemaProvider(self.app.plugin_manager).get_fields(),
]
```

これにより、GUIプラグインを追加・削除してもModulesタブの表示切替項目が
自動追従し、設定管理層とプラグイン管理層は直接結合しない。

### 3.4 移行手順

1. **`SettingsManager` を `BaseSettingsManager` に適合させる**
   - `src/core/config/settings_manager.py` の `SettingsManager` が
     `reusable_gui.core.config.settings_manager.BaseSettingsManager` を
     継承するように変更する。
2. **コアスキーマを完全化する**
   - General/History/Notifications/Font/Excluded Apps/Hotkey の全項目を
     `SettingsManager.get_settings_schema()` に列挙する。
3. **`PluginSettingsSchemaProvider` を追加する**
   - `PluginManager.get_gui_plugins()` を基に `Modules` タブの
     `show_{plugin}_tab` 項目を動的生成する。
4. **`ReusableSettingsWindow` を拡張する**
   - `_get_schema()` と保存前フック `_validate_pending_values()` を追加する。
   - `_apply_only()` / `_save_and_close()` は、検証に成功した場合のみ
     `_collect_values()` と通知・保存を実行する。
5. **`AppSettingsWindow` を新規作成し、既存 `SettingsWindow` を置き換える**
   - `src/gui/windows/settings_window.py` の内容を全面差し替える。
   - `_get_schema()` でコア・Modulesスキーマを合成する。
   - テーマ適用と翻訳キー対応をフックする。
6. **`app_main.py` の `open_settings_window()` は変更不要**
   - `self.create_toplevel(SettingsWindow, self.settings_manager)` の
     呼び出し口は変わらない。

### 3.5 影響範囲の確認

| 呼び出し元                                     | 現状の依存内容                                   | 変更後の影響                                        |
| :--------------------------------------------- | :----------------------------------------------- | :-------------------------------------------------- |
| `src/core/app_main.py: open_settings_window()` | `SettingsWindow(master, self, settings_manager)` | 変更なし（コンストラクタ互換）                      |
| `src/gui/main_gui.py`                          | `show_{plugin}_tab` でGUIプラグインのタブを制御  | 変更なし。Modulesスキーマが既存キーを生成・保存する |
| `src/core/bootstrap/application_builder.py`    | 未参照                                           | 影響なし                                            |
| `settings.json` の保存形式                     | `dict[str, Any]`                                 | 変更なし。既存の `show_{plugin}_tab` 値を継承する   |

---

## 4. グローバルホットキー機能 詳細仕様

### 4.1 要件
- デフォルトキー: `Ctrl+Shift+F`
- 動作: トリガー時にウィンドウの「表示 ⇔ 最小化」をトグルする。
- タスクバーの最小化ボタンなど、OS操作による状態変化にも追従する。
- 将来、トレイ格納などの追加状態を既存コード変更なしで組み込める設計とする。
- キー競合時は起動を継続し、ログとエラーダイアログで通知する
  （§4.6参照）。

### 4.2 レイヤー構成

```mermaid
graph TD
    subgraph "検知層 (OS依存)"
        HK["GlobalHotkeyListener\n(src/core/hotkey/)"]
    end
    subgraph "状態管理層 (アプリ内ロジック)"
        WSM["WindowStateManager\n(src/core/window/)"]
        VS["VisibleStrategy"]
        MS["MinimizedStrategy"]
    end
    subgraph "配線層"
        ED["EventDispatcher"]
        MA["MainApplication"]
    end

    HK -->|"toggle() 呼び出し"| WSM
    WSM --> VS
    WSM --> MS
    MA -->|"GLOBAL_HOTKEY_TRIGGERED を購読"| ED
    HK -.->|"dispatch"| ED
    ED -.->|"通知"| MA
    MA -->|"window_state_manager.toggle()"| WSM
```

- `GlobalHotkeyListener` は「キー入力を検知して通知する」以外の責務を持たない。
- `WindowStateManager` は「今どの状態か」「状態が変わったら何をするか」を
  `WindowState` (Enum) と `WindowStateStrategy` (Protocol) の組み合わせで
  一元管理する。
- 両者の間には直接依存を作らず、`EventDispatcher` の
  `GLOBAL_HOTKEY_TRIGGERED` イベントを介して疎結合に接続する
  （既存アーキテクチャの Pub/Sub 方針に合わせる）。

### 4.3 クラス設計

```mermaid
classDiagram
    class WindowState {
        <<enumeration>>
        VISIBLE
        MINIMIZED
    }
    class WindowStateStrategy {
        <<Protocol>>
        +enter(root: tk.Tk)
    }
    class VisibleStrategy {
        +enter(root)
    }
    class MinimizedStrategy {
        +enter(root)
    }
    class WindowStateManager {
        -_state: WindowState
        -_strategies: dict~WindowState, WindowStateStrategy~
        +show()
        +minimize()
        +toggle()
        +register_strategy(state, strategy)
    }
    class GlobalHotkeyListener {
        -_thread: threading.Thread
        -_thread_id: int
        +start(modifiers, vk_code) bool
        +start_many(registrations) bool
        +stop()
    }
    class HotkeyRegistrationManager {
        +reconfigure(enabled, combo) bool
        +reconfigure_all(global_enabled, global_combo, pinned_bindings) bool
        +history_id_for_hotkey(hotkey_id) int | None
    }
    WindowStateStrategy <|.. VisibleStrategy
    WindowStateStrategy <|.. MinimizedStrategy
    WindowStateManager --> WindowState
    WindowStateManager --> WindowStateStrategy : uses
    HotkeyRegistrationManager --> GlobalHotkeyListener : manages registrations
    GlobalHotkeyListener ..> WindowStateManager : "dispatch経由で疎結合"
```

### 4.4 ファイル配置

```text
src/core/
├── hotkey/
│   ├── __init__.py
│   ├── global_hotkey_listener.py    # Listener, HotkeyRegistration, キー文字列変換
│   ├── hotkey_registration_manager.py # 集合検証・ID採番・失敗時復元
│   └── paste_sender.py              # WindowsPasteSender
└── window/
    ├── __init__.py
    └── window_state_manager.py      # WindowState, WindowStateStrategy, WindowStateManager
```

- `hotkey/` は `clipboard/` と同じOS監視インフラの層に置き、キー入力の検知、集合登録、入力送信をUI状態管理から分離する。
- `window/` はアプリのUI状態管理として独立させ、将来トレイ格納の
  `TrayHiddenStrategy` 等を追加する際もこのパッケージ内に収める。

### 4.5 実装詳細

#### 4.5.1 `WindowState` / `WindowStateManager`

```python
# src/core/window/window_state_manager.py
from __future__ import annotations

import logging
import tkinter as tk
from enum import Enum, auto
from typing import Protocol

logger = logging.getLogger(__name__)


class WindowState(Enum):
    VISIBLE = auto()
    MINIMIZED = auto()
    # 将来追加: HIDDEN_TO_TRAY = auto()


class WindowStateStrategy(Protocol):
    def enter(self, root: tk.Tk) -> None: ...


class VisibleStrategy:
    def enter(self, root: tk.Tk) -> None:
        root.deiconify()
        root.lift()
        root.focus_force()


class MinimizedStrategy:
    def enter(self, root: tk.Tk) -> None:
        root.iconify()


class WindowStateManager:
    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._state = WindowState.VISIBLE
        self._strategies: dict[WindowState, WindowStateStrategy] = {
            WindowState.VISIBLE: VisibleStrategy(),
            WindowState.MINIMIZED: MinimizedStrategy(),
        }
        root.bind("<Unmap>", self._on_unmap, add="+")
        root.bind("<Map>", self._on_map, add="+")

    @property
    def state(self) -> WindowState:
        return self._state

    def show(self) -> None:
        self._transition_to(WindowState.VISIBLE)

    def minimize(self) -> None:
        self._transition_to(WindowState.MINIMIZED)

    def toggle(self) -> None:
        if self._state == WindowState.VISIBLE:
            self.minimize()
        else:
            self.show()

    def register_strategy(
        self, state: WindowState, strategy: WindowStateStrategy
    ) -> None:
        self._strategies[state] = strategy

    def _transition_to(self, new_state: WindowState) -> None:
        strategy = self._strategies.get(new_state)
        if strategy is None:
            logger.warning(
                "未知のウィンドウ状態への遷移が要求されました: %s", new_state
            )
            return
        strategy.enter(self._root)
        self._state = new_state

    def _on_unmap(self, event: tk.Event) -> None:
        if event.widget == self._root:
            self._state = WindowState.MINIMIZED

    def _on_map(self, event: tk.Event) -> None:
        if event.widget == self._root:
            self._state = WindowState.VISIBLE
```

#### 4.5.2 `GlobalHotkeyListener` とキー文字列変換

`GlobalHotkeyListener` は、登録ID・修飾キー・仮想キーコードを持つ `HotkeyRegistration` の集合を、単一のWindowsメッセージスレッドで処理する。`GLOBAL_HOTKEY_ID = 1` は表示/最小化キー専用の予約IDであり、ピン留め履歴のIDは `2` から採番する。

```python
@dataclass(frozen=True)
class HotkeyRegistration:
    hotkey_id: int
    modifiers: int
    vk_code: int


class GlobalHotkeyListener:
    def start(self, modifiers: int, vk_code: int) -> bool:
        """表示/最小化キーだけを登録する互換API。"""

    def start_many(self, registrations: Iterable[HotkeyRegistration]) -> bool:
        """登録集合を置き換え、失敗時は全件を解除する。"""

    def stop(self) -> None:
        """登録済みの全ホットキーを解除する。"""
```

`start_many()` は重複する登録IDを拒否し、いずれかの `RegisterHotKey` が失敗した場合は、同じスレッドで既に登録したIDを逆順に解除する。`WM_HOTKEY` の通知には `wParam` の登録IDを付け、`tk_root.after()` を介してメインスレッドのコールバックへ渡す。単一キー用の `start()` は、予約ID `1` の登録を `start_many()` へ委譲する後方互換APIとして残す。

キー文字列は `parse_hotkey_string()` と `format_hotkey()` で正規化する。修飾キーは `Ctrl`、`Alt`、`Shift`、`Win`、主キーは英数字を受け付ける。

`HotkeyRegistrationManager` は `reconfigure_all(global_enabled, global_combo, pinned_bindings)` により候補集合を検証・登録する。表示/最小化キーとピン留めキーの重複を拒否し、登録に失敗した場合は旧集合を復元する。`history_id_for_hotkey()` により、アプリケーション層はWin32の登録詳細を持たずにピン留め履歴を特定できる。

### 4.6 設定への統合

#### 4.6.1 デフォルト設定 (`src/core/config/defaults.py`)

```python
DEFAULT_USER_SETTINGS = {
    ...
    "global_hotkey_enabled": True,
    "global_hotkey_combo": "Ctrl+Shift+F",
    "pinned_hotkey_bindings": {},
}
```

#### 4.6.2 `SettingField` の追加 (`SettingsManager.get_settings_schema()`)

```python
(
    SettingField(
        key="global_hotkey_enabled",
        label="Enable Global Hotkey",
        widget_type=WidgetType.CHECKBUTTON,
        tab="General",
        group="Global Hotkey",
        default=True,
    ),
)
(
    SettingField(
        key="global_hotkey_combo",
        label="Show/Hide Hotkey",
        widget_type=WidgetType.HOTKEY_CAPTURE,
        tab="General",
        group="Global Hotkey",
        default="Ctrl+Shift+F",
    ),
)
```

#### 4.6.3 `WidgetType.HOTKEY_CAPTURE` の追加

`reusable_gui/core/config/schema.py`:

```python
class WidgetType(Enum):
    ...
    HOTKEY_CAPTURE = auto()
    """str値（例: "Ctrl+Shift+F"）。フォーカス中のキー入力を取得して
    正規化したホットキー文字列を保持する専用ウィジェット。競合検証・登録・
    エラー表示はアプリケーション側のApply/Save処理が担当する。"""
```

`reusable_gui/windows/settings_window.py` の `_render_field()` に
以下のケースを追加する（汎用ウィジェットとして実装）。

- `ttk.Entry` は直接編集不可 (`readonly`) とし、フォーカス中の
  `<KeyPress>` を捕捉して `Ctrl+Shift+F` 形式の文字列を `StringVar` に保存する。
- 修飾キー単独の押下は値を変更しない。
- 対応する修飾キーは `Ctrl` / `Alt` / `Shift` / `Win`、主キーは初期実装で
  英数字に限定する。不正な組み合わせは画面上で確定しない。
- **テスト登録ボタンは設けない。** 競合チェックはApply/Save時の1経路に統一する。

#### 4.6.4 Apply/Save時の検証と登録

UIは `GlobalHotkeyListener` の低水準な登録APIを直接呼び出さず、`HotkeyRegistrationManager` を経由して状態を変更する。

```python
class HotkeyRegistrationManager:
    def reconfigure(self, enabled: bool, combo: str) -> bool:
        """表示/最小化キーを再構成し、現在のピン留め割当を維持する。"""

    def reconfigure_all(
        self,
        global_enabled: bool,
        global_combo: str,
        pinned_bindings: Mapping[int, str],
    ) -> bool:
        """表示/最小化キーとピン留めキーの候補集合を原子的に再構成する。"""
```

設定画面で表示/最小化キーを保存する際は `reconfigure()` を使い、ピン留め履歴の割当・変更・解除・一括解除では `reconfigure_all()` を使う。後者の候補は `pinned_hotkey_bindings` として履歴IDの文字列をキー、正規化済みのキー文字列を値にして永続化する。

両APIは、候補キーの書式と集合内の重複を検証してから登録する。登録に失敗した場合は旧集合を復元し、設定または割当を保存しない。成功時だけ新しい設定を保存し、履歴一覧を更新する。

### 4.7 アプリライフサイクルへの組み込み

```mermaid
sequenceDiagram
    participant Builder as ApplicationBuilder
    participant App as MainApplication
    participant WSM as WindowStateManager
    participant HRM as HotkeyRegistrationManager
    participant HK as GlobalHotkeyListener
    participant ED as EventDispatcher

    Builder->>WSM: with_window_state_manager(master)
    Builder->>HK: with_global_hotkey_listener(master, dispatch経由callback)
    Builder->>HRM: with_hotkey_registration_manager(listener)
    Builder->>App: build()
    App->>App: on_ready()
    App->>HRM: reconfigure_all(グローバル設定, pinned_hotkey_bindings)
    Note over HRM: 失敗時はエラー通知、起動は継続

    Note over HK,ED: ユーザーが登録済みのホットキーを押下
    HK->>ED: dispatch("GLOBAL_HOTKEY_TRIGGERED", hotkey_id)
    ED->>App: 通知
    App->>WSM: toggle()

    Note over App: Apply/Saveによる設定変更
    App->>HRM: 設定画面またはピン留め操作で再構成

    Note over App: on_closing() / shutdown()
    App->>HRM: stop() (確実な解放)
```

#### 4.7.1 `ApplicationBuilder` への追加

```python
def with_window_state_manager(self, master: tk.Tk) -> ApplicationBuilder:
    from src.core.window.window_state_manager import WindowStateManager

    self.window_state_manager = WindowStateManager(master)
    return self


def with_global_hotkey_listener(self, master: tk.Tk) -> ApplicationBuilder:
    if not self.event_dispatcher:
        raise ConfigError("イベントディスパッチャが初期化されていません")
    from src.core.hotkey.global_hotkey_listener import GlobalHotkeyListener

    self.hotkey_listener = GlobalHotkeyListener(
        master,
        on_triggered=lambda hotkey_id: self.event_dispatcher.dispatch(
            "GLOBAL_HOTKEY_TRIGGERED", hotkey_id
        ),
    )
    return self


def with_hotkey_registration_manager(self) -> ApplicationBuilder:
    from src.core.hotkey.hotkey_registration_manager import HotkeyRegistrationManager

    self.hotkey_registration_manager = HotkeyRegistrationManager(self.hotkey_listener)
    return self
```

`build()` の必須コンポーネント検証リストと `MainApplication` コンストラクタに
`window_state_manager`, `hotkey_registration_manager` を追加する。

#### 4.7.2 `MainApplication` への追加

- `on_ready()` は、設定値を正規化したピン留め割当とともに `_reconfigure_hotkeys_from_settings()` で登録する。登録に失敗しても、エラーを表示してアプリケーションの起動は継続する。
- `GLOBAL_HOTKEY_TRIGGERED` は登録IDを伴う。予約ID `1` は `WindowStateManager.toggle()` を呼び、ピン留めIDは `history_id_for_hotkey()` で履歴IDへ変換して、クリップボード更新・通知音・75ms後の `WindowsPasteSender` による貼り付けを行う。
- ピン留め割当の設定・変更・解除・一括解除は、再構成成功後だけ `pinned_hotkey_bindings` を保存し、履歴一覧を更新する。ピン解除、履歴削除、全履歴削除時も対応する割当を解除する。
- `shutdown()` は `HotkeyRegistrationManager.stop()` を呼び、登録済みの全IDを解除する。

### 4.8 競合時の挙動仕様

| ケース                         | 挙動                                                                                                                                |
| :----------------------------- | :---------------------------------------------------------------------------------------------------------------------------------- |
| 起動時に登録集合が競合         | `reconfigure_all()` が `False` を返す。ログwarning出力とエラーダイアログ表示後、アプリは起動を継続し、ホットキー機能のみ無効にする。 |
| Apply/Save時に新しいキーが競合 | エラーを表示してApply/Saveを中止する。候補設定は `settings.json` に保存せず、可能な限り従来の有効なホットキー登録を維持・復元する。 |
| 不正なキー形式                 | エラーを表示してApply/Saveを中止する。既存設定・登録状態を変更しない。                                                              |
| アプリ終了時                   | `shutdown()` で必ず `UnregisterHotKey` を実行し、他アプリが同キーを登録できる状態に戻す。                                           |

---

## 5. 影響を受けるファイル一覧

| ファイル                                                 | 変更種別                                                                                      |
| :------------------------------------------------------- | :-------------------------------------------------------------------------------------------- |
| `src/gui/windows/settings_window.py`                     | 全面置き換え（`reusable_gui` 版継承、スキーマ合成・保存前検証）                               |
| `src/core/config/settings_manager.py`                    | `BaseSettingsManager` 継承化、コアスキーマ拡充                                                |
| `src/core/config/defaults.py`                            | `global_hotkey_*` デフォルト値追加                                                            |
| `src/plugins/settings_schema_provider.py`（新規）        | GUIプラグイン由来のModulesスキーマ生成                                                        |
| `reusable_gui/core/config/schema.py`                     | `WidgetType.HOTKEY_CAPTURE` 追加                                                              |
| `reusable_gui/windows/settings_window.py`                | `_get_schema()`、`_validate_pending_values()` フック、`HOTKEY_CAPTURE` のレンダリング処理追加 |
| `src/core/hotkey/__init__.py`（新規）                    | 追加                                                                                          |
| `src/core/hotkey/global_hotkey_listener.py`（新規）      | OSホットキーの検知、キー文字列変換                                                            |
| `src/core/hotkey/hotkey_registration_manager.py`（新規） | 集合検証、ID採番、登録切替、失敗時の復元                                                       |
| `src/core/hotkey/paste_sender.py`（新規）                | アクティブウィンドウへの `Ctrl+V` 送信                                                        |
| `src/core/window/__init__.py`（新規）                    | 追加                                                                                          |
| `src/core/window/window_state_manager.py`（新規）        | ウィンドウ状態遷移とStrategy管理                                                              |
| `src/core/bootstrap/application_builder.py`              | Hotkey・Window関連コンポーネントのビルドステップ追加                                          |
| `src/core/app_main.py`                                   | ライフサイクル・イベント購読・依存性受け取り追加                                              |
| `locales/en.json` / `locales/ja.json`                    | ホットキー設定、Modulesタブのラベル翻訳キー追加                                               |

---

## 6. 検証計画

1. **単体テスト（`pytest`）**
   - `parse_hotkey_string` / `format_hotkey` の相互変換（正常系・異常系）。
   - `WindowStateManager` の状態遷移（`show()` → `VISIBLE`、
     `minimize()` → `MINIMIZED`、`toggle()` の往復）。
   - `HotkeyRegistrationManager` の再構成判断（無効化、同一設定、
     競合時に既存設定を維持すること）をモックで検証。
   - `SettingsManager.get_settings_schema()` が全コア設定と
     `HOTKEY_CAPTURE` 項目を含むことの検証。
   - `PluginSettingsSchemaProvider` がGUIプラグインごとに
     `show_{plugin}_tab` の `SettingField` を生成することの検証。
2. **手動確認（OS依存のため）**
   - デフォルトキーでウィンドウの表示/最小化がトグルすることを確認。
   - タスクバーの最小化ボタン操作後にホットキーを押し、状態追従を確認。
   - 別プロセスで同じキーを登録した状態で起動し、競合エラーダイアログが
     出ることを確認。
   - 設定画面でキー組み合わせを変更してApply/Saveした際、競合なら
     設定が保存されず旧キーが継続することを確認。
   - 競合しない変更では、旧キーが反応せず新キーが反応することを確認。
   - GUIプラグインの表示切替がModulesタブに表示され、保存・再起動後も
     `ClipWatcherGUI` のタブ状態に反映されることを確認。
   - アプリ終了後、同じキーが他アプリで登録可能になっていることを確認。
3. **既存機能への影響確認**
   - 設定画面の全タブ（General/History/Notifications/Font/Excluded Apps/Modules）
     が移行後も同じ項目を保存・復元できることを回帰確認。
   - `Export/Import/Restore Defaults` ボタンが従来通り動作することを確認。
   - 既存の `settings.json` に含まれる `show_{plugin}_tab` 値を読み込んだ場合も、
     Modulesタブとメイン画面の表示状態へ正しく反映されることを確認。

---

## 7. 確定事項

- デフォルトのグローバルホットキーは `Ctrl+Shift+F` とする。
- 表示/最小化キーには予約ID `1` を使用し、ピン留め履歴キーはID `2` 以降を使用する。
- ピン留め履歴の割当は `pinned_hotkey_bindings` に保存し、重複キーを拒否する。登録失敗時は旧集合を復元し、終了時は全IDを解除する。
- ホットキーの動作は、予約IDではメインウィンドウの表示/最小化トグル、ピン留めIDでは対象履歴の自動貼り付けとする。
- `HOTKEY_CAPTURE` ウィジェットにはテスト登録ボタンを設けない。
  競合検証・登録切替はApply/Save時に `HotkeyRegistrationManager` の
  単一経路で実施し、失敗時は設定を保存しない。
- `Modules` タブは本改造のスコープに含め、
  `PluginSettingsSchemaProvider` による動的スキーマとして実装する。
- システムトレイ常駐は本改造では実装しない。ただし、
  `WindowState` と `WindowStateStrategy` の拡張で将来追加可能な構造にする。

## 8. 将来の検討事項（本改造では対応不要）

- **トレイ格納状態**: スコープ外であり、トレイアイコンやWndProcを含む実装は
  行わない。将来 `HIDDEN_TO_TRAY` と `TrayHiddenStrategy` を追加できるよう、
  `WindowState` / `WindowStateStrategy` の拡張点だけを維持する。
- **`show_*_settings_tab` の扱い**: 現在はUIとして提供されず、
  実行時にも利用されていない休眠設定である。今回ただちに削除する必要はない。
  既存の `settings.json` 値と `defaults.py` のキーは後方互換のため残し、
  スキーマおよび新設定画面には表示しない。将来、正式な設定画面タブ切替を
  要求する場合はスキーマ化し、不要と決定した場合は設定ファイル移行を伴う
  段階的な廃止を行う。
