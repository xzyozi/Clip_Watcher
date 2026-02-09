# 内部ヒストリ保存に関する調査報告

## 概要
ClipWatcherのクリップボード履歴に関して、以下の2点の問題について調査を行いました。

1.  **履歴の消失**: アプリケーションの強制終了時などに履歴が保存されない。
2.  **初期表示の不具合**: アプリケーション起動時、読み込まれているはずの履歴がGUIに表示されない。

## 調査結果 1: 履歴の消失について

### 現状の動作
1.  **読み込み**: アプリケーション起動時、`ClipboardMonitor.__init__` 内で `_load_history_from_file()` が呼び出され、`history.json` から履歴が読み込まれます。
2.  **保存**: アプリケーションの正常終了時（ウィンドウを閉じるなど）に、`MainApplication.shutdown()` が呼び出され、その中で `self.monitor.save_history_to_file()` が実行されます。
3.  **更新時**: クリップボードの内容が更新された際（`_update_history_with_new_entry`）、内部のメモリ上の履歴リスト (`self.history`) は更新されますが、**ファイルへの保存処理は行われません**。

### 問題点
*   `save_history_to_file()` は `MainApplication.shutdown()` からのみ呼び出されています。
*   したがって、タスクマネージャーからの強制終了や、OSのクラッシュ、電源断などでアプリケーションが予期せず終了した場合、起動後にメモリ上に追加された履歴はファイルに書き込まれていないため消失します。

### 改善案
履歴の消失を防ぐためには、以下のいずれか（または組み合わせ）の実装が推奨されます。

1.  **定期保存**: `ClipboardMonitor` 内で `tkinter.after` などを利用し、定期的（例: 5分ごと）に `save_history_to_file()` を呼び出す。
2.  **更新時保存**: `_update_history_with_new_entry` が呼ばれるたびに保存を行う。
    *   *注意*: ディスクI/Oの頻度が高くなるため、パフォーマンスへの影響を考慮する必要があります。
3.  **デバウンス保存**: 更新があった場合、一定時間（例: 5秒）後に保存するタイマーをセットし、連続して更新がある場合はタイマーをリセットする。これにより、頻繁な更新時のI/Oを抑制しつつ、比較的リアルタイムに近い保存が可能になります。

---

## 調査結果 2: GUI初期表示の不具合について

### 現状の動作
1.  **データ保持**: `ClipboardMonitor` は初期化時に `history.json` からデータを正しく読み込み、メモリ上 (`self.history`) に保持しています。
2.  **GUI構築**: `MainApplication` が `ClipWatcherGUI` を構築しますが、この時点では履歴データは GUI コンポーネントに渡されません。
3.  **更新メカニズム**: GUI の履歴リストは、主に `ClipboardMonitor` からのコールバック (`update_callback`) によって更新されます。このコールバックは、クリップボードの内容に変更があった場合や、明示的に `_trigger_gui_update` が呼ばれた場合に発火します。
4.  **起動時のフロー**:
    *   `MainApplication.on_ready()` で `monitor.start()` が呼ばれ、監視スレッドが開始します。
    *   監視スレッドは現在のクリップボード内容を取得し、前回の内容 (`last_clipboard_data`、初期値は空) と比較します。
    *   差分がある場合のみ更新処理が走り、GUI が更新されます。

### 原因
*   **初期描画の欠落**: `MainApplication` の初期化および `on_ready` フローにおいて、**ファイルから読み込んだ既存の履歴データを GUI に反映させる処理（`update_gui` の明示的な呼び出し）が行われていません。**
*   そのため、ユーザーが新たにコピーを行うか、監視スレッドが「現在のクリップボード内容が初期値と異なる」と判断するまで、履歴リストは空のままとなります。

### 改善案
`MainApplication.on_ready()` メソッド（または `build` メソッドの最後）において、初期化完了後に明示的に GUI 更新を呼び出す処理を追加する必要があります。

```python
# src/core/app_main.py (修正イメージ)

def on_ready(self) -> None:
    self._set_state(ApplicationState.READY)
    
    # 追加: 初期データをGUIに反映させる
    # last_clipboard_data は読み込み時点では空かもしれないが、履歴(get_history)は存在する可能性がある
    self.update_gui(self.monitor.last_clipboard_data, self.monitor.get_history())
    
    self.monitor.start()
    self._set_state(ApplicationState.RUNNING)
```

## 結論
1.  **保存漏れ**: 履歴の保存が終了時にしか行われていないため、不測の事態に備えて「更新ごとの保存」または「定期保存」を導入すべきです。
2.  **表示漏れ**: 起動時に読み込んだ履歴を GUI に渡す処理が抜けているため、`MainApplication.on_ready` で初期描画を行うよう修正すべきです。
