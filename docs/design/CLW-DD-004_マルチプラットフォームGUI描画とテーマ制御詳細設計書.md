---
title: "マルチプラットフォームGUI描画とテーマ制御詳細設計書"
file_name: "CLW-DD-004_マルチプラットフォームGUI描画とテーマ制御詳細設計書.md"
document_type: "detailed_design"
version: "1.1"
created_at: "2026-10-12"
updated_at: "2026-11-04"
author: "ClipWatcher Development Team"
purpose: "Python標準モジュール縛りの方針のもと、Windows/macOS/Linuxにおける一貫したTkinter/ttk描画、Aquaテーマ制御、OSダークモード同期、Treeview/IconManager連携、およびレガシー環境起動ガード仕様を定義するため"
related_documents:
  - "CLW-BD-001_ClipWatcher全体アーキテクチャ基本設計書.md"
  - "CLW-BD-002_ClipWatcher機能基本設計書.md"
  - "docs/issues/CW-0073.md"
---

# 詳細設計書（マルチプラットフォームGUI描画とテーマ制御）
**標準Tkinterによるクロスプラットフォーム描画・Aqua制御・Treeview/アイコン管理・起動ガード仕様**

| 項目           | 内容                                                                     |
| :------------- | :----------------------------------------------------------------------- |
| 文書番号       | CLW-DD-004                                                               |
| ファイル名     | CLW-DD-004_マルチプラットフォームGUI描画とテーマ制御詳細設計書.md         |
| ドキュメント名 | マルチプラットフォームGUI描画とテーマ制御詳細設計書                      |
| 版数           | Rev.1.1                                                                  |
| 改訂日         | 2026-11-04                                                               |
| 作成日         | 2026-10-12                                                               |
| 作成者         | ClipWatcher Development Team                                             |

---

## 1. 概要と設計思想

### 1.1 標準モジュール縛り（ゼロインストールのポータビリティ）
本アプリケーションは、サードパーティ製GUIフレームワーク（PyQt, CustomTkinter等）や過度な外部依存を排し、**Python標準ライブラリ（`tkinter`, `ttk`）のみで完結するゼロインストール・高ポータビリティ**を基本設計思想とします。
ユーザーが追加の仮想環境やパッケージマネージャー（`uv`, `pip`）を意識することなく、OSに導入されている素の `python3 clip_watcher.py` だけで安全・快適に起動できることを目指します。

### 1.2 本書のスコープと単一責任 (SSOT)
本書は以下の制御仕様に関する正本（SSOT）を定義します：
1. **プラットフォーム別 ttk テーマの選定**: Windows, macOS (Aqua), Linux (clam/default) の描画パイプライン制御
2. **macOS Cocoa レンダリングと OS 外観同期**: システム外観（Dark/Light）とアプリ内カラーパレットの調和
3. **レガシーランタイム（Tk 8.5 / Python < 3.10）起動ガード**: macOS 組み込みの Tk 8.5 環境における黒画面化防止と安全な終了案内 (#211, #213)
4. **Treeview スタイルと行高制御**: 履歴一覧（`ttk.Treeview`）の Aqua / clam 最適化、タグ色保護、および動的 `rowheight` 制御 (#195, #196)
5. **IconManager と世代管理キャッシュ**: テーマ切替時の画像再バインドとピン留めテキストフォールバック (#203, #212)
6. **ウィジェットツリーへのスタイル伝播**: `ThemeManager.apply_theme_to_widget_tree()` による Tk / ttk ウィジェットの色整合性担保

---

## 2. プラットフォーム別レンダリング仕様

| プラットフォーム | 使用テーマ | 背景・ウィジェット制御方針 | 留意点・制約 |
| :--- | :--- | :--- | :--- |
| **Windows** | `clam` / `default` | `ttk.Style` + ウィジェットツリー巡回でフルカラー制御 | ネイティブタイトルバーとの親和性良好 |
| **macOS (Tk 8.6+)** | `aqua` 維持 | OSダークモード判定と同期し、Dark/Lightパレット適用 | `clam`切り替え禁止（CALayer破壊防止） |
| **macOS (Tk 8.5 / Python 3.9)** | 対象外（起動中断） | **起動ガードによるネイティブ案内と安全終了** | Tk 8.5 / Python < 3.10 は起動直後に終了ダイアログ表示 (#213) |
| **Linux (X11)** | `clam` / `default` | `ttk.Style` + ウィジェットツリー巡回でフルカラー制御 | X11/Wayland環境依存なし |

### 2.1 macOS (Aqua) レンダリングの特殊性と制約
- **Cocoa ネイティブ描画**: macOS の `aqua` テーマは macOS の WindowServer / CALayer と直接連携して描画されます。`style.theme_use("clam")` 等を実行すると Cocoa サーフェスとの同期が外れ、ウィンドウ全体が黒一色（未描画）になります。そのため macOS では **`aqua` テーマの維持が必須** です。
- **システム外観との連動**: Tk 8.6.10+ の `aqua` は OS のシステムアピアランス（Dark / Light）に従って親フレームの背景色を自動決定します。アプリ側が OS と逆の明暗テーマを強制設定すると、親背景と文字色が同化して文字が消失（キメラ描画）するため、OS の外観（`defaults read -g AppleInterfaceStyle`）とテーマを一致させます。

### 2.2 Tk 8.5（macOS システム標準 Python 3.9）の起動ガード仕様 (#211, #213)
- **Tk 8.5 の黒画面化問題**: macOS の Xcode CommandLineTools に付属する Python 3.9.6 にバンドルされた Tk 8.5 は、CoreAnimation レンダリングに対応しておらず、起動時にウィンドウ全体が黒画面（Blank window）となり一切操作不能になる致命的な問題があります。
- **起動ガードの契約**: `src/event_handlers/__init__.py` の `start_app()` は、GUI初期化直後に `is_legacy_macos_tk()`（Tk < 8.6）または `sys.version_info < (3, 10)` を検知した場合、ネイティブアラート（`osascript` または `messagebox.showerror`）で「本アプリケーションの動作には Tk 8.6 以上 (Python 3.10+) が必要です」と明示的に案内し、`root.destroy()` で安全に起動を中断します。
- **ThemeManager 内のフォールバック位置づけ**: `ThemeManager.apply_theme()` に存在する `tk_ver < 8.6` での Light 強制フォールバックは、起動ガード外の単体テストや特殊環境向けの防御的セーフティネットとして維持されます。

---

## 3. テーマ決定と描画制御フロー

```mermaid
flowchart TD
    Start([アプリ起動 / start_app]) --> CheckLegacy{レガシー環境判定\nTk < 8.6 or Py < 3.10}
    CheckLegacy -->|該当 (macOS)| ShowAlert[ネイティブアラート表示\nTk 8.6+ への誘導案内]
    ShowAlert --> Abort([root.destroy / 安全終了])
    
    CheckLegacy -->|適合| CheckOS{OS 判定}
    CheckOS -->|darwin| CheckDarkMode{OS 外観判定\nAppleInterfaceStyle}
    CheckOS -->|その他| ApplyCustom[設定テーマを適用]
    
    CheckDarkMode -->|Dark| SetDark[自動選択: Dark テーマ]
    CheckDarkMode -->|Light| SetLight[自動選択: Light テーマ]
    
    SetDark --> MaintainAqua[ttk テーマ: aqua 維持]
    SetLight --> MaintainAqua
    ApplyCustom --> ApplyTtkStyle[ttk テーマ: clam / default]
    
    MaintainAqua --> ApplyStyles[Treeview / ttk スタイル設定]
    ApplyTtkStyle --> ApplyStyles
    
    ApplyStyles --> ApplyWidgetTree[ウィジェットツリー色適用\nText / Entry / PanedWindow]
    ApplyWidgetTree --> ForceRefresh[初回アイドル更新\nroot.update_idletasks]
    ForceRefresh --> End([描画完了 / mainloop])
```

---

## 4. モジュール・クラス詳細仕様

### 4.1 `ThemeManager` (`src/gui/theme_manager.py`)

#### A. `apply_theme(theme_name: str) -> None`
- **事前条件**: `self.root` が初期化済みであること。
- **処理手順**:
  1. `sys.platform == "darwin"` の場合：
     - `tk.TkVersion < 8.6` の判定を実施。
     - `TkVersion < 8.6` の場合は `theme_name = "light"` を強制設定。
     - `TkVersion >= 8.6` の場合は `is_macos_dark_mode()` に基づき `"dark"` または `"light"` を自動選択。
  2. `style = ttk.Style(self.root)` を取得。
  3. `sys.platform == "darwin"` かつ `"aqua" in style.theme_names()` の場合は `aqua` テーマを維持（`clam` への切替を行わない）。
  4. 各種 `ttk` スタイル（`TFrame`, `TLabel`, `TButton`, `Treeview` 等）にテーマ色を設定。
  5. `self.apply_theme_to_widget_tree(self.root, theme)` を呼び出し、非 ttk ウィジェットへ色を伝播。

#### B. `apply_theme_to_widget_tree(widget: tk.Widget, theme: dict) -> None`
- **対象ウィジェットと適用属性**:
  - `tk.Text`: `bg=theme["listbox_bg"]`, `fg=theme["listbox_fg"]`, `insertbackground=theme["fg"]`, `selectbackground=theme["select_bg"]`, `selectforeground=theme["select_fg"]`
  - `tk.Listbox`: `bg=theme["listbox_bg"]`, `fg=theme["listbox_fg"]`, `selectbackground=theme["select_bg"]`, `selectforeground=theme["select_fg"]`
  - `tk.Entry` (`CustomEntry`): `bg=theme["entry_bg"]`, `fg=theme["entry_fg"]`, `insertbackground=theme["fg"]`, `selectbackground=theme["select_bg"]`, `selectforeground=theme["select_fg"]`
  - `tk.PanedWindow`: `bg=theme["frame_bg"]`
  - `tk.Button`: `bg=theme["button_bg"]`, `fg=theme["button_fg"]`, `activebackground=theme["select_bg"]`, `activeforeground=theme["select_fg"]`
  - `tk.Checkbutton` / `tk.Radiobutton`: `bg=theme["button_bg"]`, `fg=theme["button_fg"]`, `activebackground=theme["select_bg"]`, `activeforeground=theme["select_fg"]`, `selectcolor=theme["frame_bg"]`
  - `tk.Label`: `bg=theme["bg"]`, `fg=theme["label_fg"]`

### 4.2 `ttk.Treeview` と履歴一覧描画制御 (#195, #196)

履歴一覧コンポーネント（`HistoryListComponent`）は `tk.Listbox` から `ttk.Treeview` へ移行し、専用スタイル `History.Treeview` を用いてプラットフォームごとの描画を最適化します。
- **Aqua テーマ (macOS)**: 選択状態の背景・前景色には macOS システムカラー（`systemHighlight`, `systemHighlightText`）をマッピングし、ネイティブ Cocoa と完全連動する。
- **clam / default テーマ (Windows/Linux)**: ダークテーマ時に `pinned` タグ付き行の選択背景色が崩れる Tkinter/ttk の描画問題を防止するため、`theme["select_bg"]` / `theme["select_fg"]` を明示的にスタイルマップへバインドする。
- **フォントと行高動的制御**: ユーザー設定フォントを全行に適用するため `"history_item"` タグを用い、フォントの文字高とアイコンサイズ（16px）に基づき `rowheight` を動的に再計算して設定する。

### 4.3 `IconManager` とピン留め表示制御 (#203, #212)

- **世代管理キャッシュ (Generation Cache)**: `IconManager` はアイコン・アクション画像を保持し、ダーク/ライトテーマ切り替え時に世代番号（`cache_generation`）をインクリメントして古い画像参照を破棄・再生成する。これによりテーマ切替時のメモリリークと画像不整合を防止する。
- **ピン留めフォールバック**: 画像アイコンが何らかの理由で取得できない場合、描画破壊を防ぐためテキストシンボル `📌` への明示的フォールバックを行う (#212)。

### 4.4 `PlatformUtils` (`src/utils/platform_utils.py`)

#### `is_macos_dark_mode() -> bool`
- **機能概要**: macOS のシステム外観設定がダークモードであるかを判定する。
- **実装方式**: `defaults read -g AppleInterfaceStyle` をサブプロセスで実行（タイムアウト 1.0秒）。標準出力が `"Dark"` の場合 `True`、それ以外（キー非存在、Lightモード、エラー時）は `False` を返却。

#### `resolve_safe_font_family(preferred_family: str | None = None) -> str` (#197)
- **機能概要**: プラットフォーム上で確実に利用可能な安全なフォントファミリー名を解決する。
- **解決順序**: macOS では `"Helvetica Neue"`, `"Hiragino Sans"` 等、Windows では `"Segoe UI"`, `"Yu Gothic UI"` 等、Linux では `"DejaVu Sans"` 等を優先し、未導入時は `"TkDefaultFont"` にフォールバックする。

---

## 5. 初回描画の安定化契約 (Geometry & Idle Tasks)
macOS Tkinter では、ウィンドウ生成直後にイベントループへ入る際、ウィンドウの描画サーフェス（CALayer）の初期割り当てが遅延して黒い矩形が残る現象を防ぐため、以下の契約を義務付けます：
1. `ClipWatcherGUI.__init__` 完了直後に `master.update_idletasks()` を実行し、配置確定を強制する。
2. 診断ログ `[DIAG-GUI]` を出力し、Notebook タブ数およびルート子ウィジェット数を記録する。

---

## 6. 検証とテスト方針

1. **単体テスト (`tests/test_theme_manager.py`)**:
   - `TkVersion < 8.6` 模擬環境における `light` テーマ強制フォールバックの検証。
   - `sys.platform == "darwin"` における `aqua` テーマ維持の検証。
   - `tk.Entry`, `tk.Text`, `tk.PanedWindow` への色伝播の検証。
2. **実機検証マトリックス**:
   - macOS システム標準 Python 3.9 (Tk 8.5) 環境でのネイティブアラートによる起動ガード終了案内。
   - Python 3.10+ (Tk 8.6.13+) 環境での Dark Mode / Light Mode 連動描画。
   - Windows 10/11 環境での既存テーマ動作の完全互換性。

---

## 7. 改訂履歴

| 版数    | 改訂日     | 変更者                      | 変更内容・変更理由 (Why)                                                                                                    |
| :------ | :--------- | :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------- |
| Rev.1.0 | 2026-10-12 | ClipWatcher Development Team| 初版作成。標準Tkinterによるクロスプラットフォーム描画、Aqua制御、Tk 8.5フォールバック仕様を定義。                             |
| Rev.1.1 | 2026-11-04 | Antigravity                 | Tk 8.5起動ガード仕様（#213）、Treeview/IconManager/フォント解決仕様の追記、`apply_theme_to_widget_tree` 表の実装整合（F-02, F-06）。 |
