# Network API 実装手順書

本ドキュメントは、「EXTENSIBILITY_PROPOSAL_STD_LIB.md」で提案された「ネットワークインターフェース (Local Network API)」機能の実装手順を詳細に記述する。

## 0. 概要と目標

ローカルネットワークからのHTTPリクエストに応じて、クリップボードの取得・設定を行うAPIサーバーを実装する。この機能はセキュリティを考慮し、デフォルトで無効とし、設定画面から有効化できるようにする。

- **主要な実装ファイル:**
    - **新規作成**: `src/core/network_api_server.py` - APIサーバーのコアロジック
    - **修正**: `src/core/config/settings_manager.py` と `src/core/config/defaults.py` - 設定項目の追加
    - **修正**: `src/core/app_main.py` - アプリケーション起動・終了時のサーバー制御
    - **修正**: `src/gui/windows/settings_window.py` - 設定画面のUI追加
    - **修正**: `src/event_handlers/main_handlers.py` - 設定変更イベントの処理

---

## Step 1: 設定項目の追加

まず、API機能に必要な設定項目をデフォルト値と共に定義する。

1.  **`src/core/config/defaults.py` を編集:**
    `DEFAULT_SETTINGS` ディクショナリに `network_api` のセクションを追加する。

    ```python
    # 既存のDEFAULT_SETTINGSに追加
    DEFAULT_SETTINGS = {
        # ... 既存の設定 ...
        "network_api": {
            "enabled": False,
            "host": "127.0.0.1",
            "port": 8181,
            "api_key": ""
        }
    }
    ```

2.  **`src/core/config/settings_manager.py` を修正:**
    `SettingsManager` クラスに、初回起動時にAPIキーを自動生成するロジックを追加する。

    - `__init__` や `load_settings` の中で、`network_api` の設定を読み込んだ後、`api_key` が空文字列であれば、新しいキーを生成して設定を更新する。

    ```python
    import secrets

    # SettingsManagerクラス内
    def load_settings(self):
        # ... 既存の読み込み処理 ...
        
        # APIキーが未設定の場合、セキュアなキーを自動生成
        if not self.settings.get("network_api", {}).get("api_key"):
            if "network_api" not in self.settings:
                self.settings["network_api"] = {} # セクションごとない場合
            
            new_key = secrets.token_hex(16)
            self.settings["network_api"]["api_key"] = new_key
            self.save_settings() # 生成したキーを保存
    ```

---

## Step 2: APIサーバーのコアロジック実装

HTTPリクエストを処理するサーバー本体を新しいファイルに作成する。

1.  **`src/core/network_api_server.py` を新規作成:**
    - `http.server` と `threading` を利用して、バックグラウンドで動作するサーバーを構築する。
    - クリップボード操作は、既存のアプリケーションの機能と連携するため、コールバック関数などを経由して行う。

    ```python
    # src/core/network_api_server.py

    import http.server
    import socketserver
    import threading
    import json
    from typing import Callable

    class ApiRequestHandler(http.server.BaseHTTPRequestHandler):
        # クラス変数として設定値やコールバックを保持
        API_KEY: str = ""
        get_clipboard_content: Callable[[], str]
        set_clipboard_content: Callable[[str], None]

        def _authenticate(self) -> bool:
            """リクエストヘッダーのAPIキーを検証する"""
            auth_header = self.headers.get("X-Api-Key")
            return auth_header is not None and auth_header == self.API_KEY

        def _send_response(self, code: int, data: dict):
            """JSONレスポンスを送信する"""
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        def do_GET(self):
            """GET /clipboard: クリップボードの内容を取得"""
            if not self._authenticate():
                return self._send_response(403, {"status": "error", "message": "Authentication failed."})
            
            if self.path == "/clipboard":
                content = self.get_clipboard_content()
                self._send_response(200, {"status": "success", "content": content})
            else:
                self._send_response(404, {"status": "error", "message": "Not Found."})

        def do_POST(self):
            """POST /clipboard: クリップボードに内容を設定"""
            if not self._authenticate():
                return self._send_response(403, {"status": "error", "message": "Authentication failed."})

            if self.path == "/clipboard":
                content_len = int(self.headers.get("Content-Length"))
                post_body = self.rfile.read(content_len)
                try:
                    data = json.loads(post_body)
                    new_content = data.get("content")
                    if new_content is None:
                        raise ValueError("Missing 'content' key")
                    
                    self.set_clipboard_content(new_content)
                    self._send_response(200, {"status": "success", "message": "Clipboard updated."})

                except (json.JSONDecodeError, ValueError) as e:
                    self._send_response(400, {"status": "error", "message": f"Bad Request: {e}"})
            else:
                self._send_response(404, {"status": "error", "message": "Not Found."})


    class NetworkApiServer(threading.Thread):
        def __init__(self, host: str, port: int, api_key: str, get_cb: Callable, set_cb: Callable):
            super().__init__(daemon=True)
            ApiRequestHandler.API_KEY = api_key
            ApiRequestHandler.get_clipboard_content = get_cb
            ApiRequestHandler.set_clipboard_content = set_cb
            
            socketserver.TCPServer.allow_reuse_address = True
            self.httpd = socketserver.TCPServer((host, port), ApiRequestHandler)

        def run(self):
            """サーバーを起動する"""
            self.httpd.serve_forever()

        def stop(self):
            """サーバーを停止する"""
            self.httpd.shutdown()
            self.httpd.server_close()
    ```

---

## Step 3: アプリケーション本体への統合

APIサーバーをアプリケーションのライフサイクルに合わせて起動・停止させる。

1.  **`src/core/app_main.py` （または同等のメインファイル）を修正:**
    - `NetworkApiServer` をインポートする。
    - アプリケーションの初期化時に、設定を読み込み、`network_api.enabled` が `True` ならサーバーを起動する。

    ```python
    # app_main.py の Application クラスなど
    from .network_api_server import NetworkApiServer
    
    class AppMain:
        def __init__(self, settings_manager):
            self.settings_manager = settings_manager
            self.network_server = None
            # ...
            self.start_services()

        def get_clipboard_for_api(self) -> str:
            # GUIスレッドと同期が必要な場合、適切な仕組み（例: queue）を使う
            return self.clipboard_monitor.get_content()

        def set_clipboard_for_api(self, text: str):
            # 同様にGUIスレッドとの同期を考慮
            self.clipboard_monitor.set_content(text)

        def start_services(self):
            """各種サービスを起動する"""
            self.update_network_server()

        def update_network_server(self):
            """設定に基づいてAPIサーバーを起動・停止する"""
            config = self.settings_manager.get("network_api")
            
            # サーバーが起動中なら一旦停止
            if self.network_server:
                self.network_server.stop()
                self.network_server.join() # 停止を待つ
                self.network_server = None
            
            # 設定が有効なら、新しい設定で再起動
            if config.get("enabled"):
                self.network_server = NetworkApiServer(
                    host=config.get("host"),
                    port=int(config.get("port")),
                    api_key=config.get("api_key"),
                    get_cb=self.get_clipboard_for_api,
                    set_cb=self.set_clipboard_for_api
                )
                self.network_server.start()

        def on_exit(self):
            """アプリケーション終了処理"""
            if self.network_server:
                self.network_server.stop()
            # ...
    ```

2.  **`src/event_handlers/main_handlers.py` （または設定変更を処理する場所）を修正:**
    設定が変更・保存された後に `app_main.update_network_server()` を呼び出すイベントハンドラを追加する。これにより、設定画面での変更が即座に反映される。

---

## Step 4: 設定画面UIの実装

ユーザーがAPI設定を変更できるGUIを `SettingsWindow` に追加する。

1.  **`src/gui/windows/settings_window.py` を修正:**
    - `ttk.Labelframe` を使って「Network API設定」セクションを作成する。
    - **有効/無効**: `ttk.Checkbutton` を配置。
    - **ホスト**: `ttk.Combobox` を使い、`"127.0.0.1"` と `"0.0.0.0"` を選択肢として提供。
    - **ポート**: `ttk.Entry` とバリデーション（数値のみ）を配置。
    - **APIキー**: `ttk.Entry` を読み取り専用(`readonly`)で配置。隣に「再生成」ボタンと「コピー」ボタンを置く。
    - **セキュリティ警告**: ホストで `"0.0.0.0"` が選択された場合に表示される `ttk.Label` を追加する。

    ```python
    # SettingsWindowクラスのUI構築部分に追加
    
    # --- Network API Frame ---
    api_frame = ttk.Labelframe(self, text="Network API")
    api_frame.pack(fill="x", padx=10, pady=5)

    # Enable/Disable Checkbox
    self.api_enabled_var = tk.BooleanVar()
    api_check = ttk.Checkbutton(api_frame, text="Enable Network API", variable=self.api_enabled_var)
    api_check.pack(anchor="w")

    # Host, Port
    # ... Combobox for host, Entry for port
    
    # API Key
    # ... readonly Entry, Regenerate Button, Copy Button

    # Warning Label
    self.api_warning_label = ttk.Label(api_frame, text="Warning: Allowing access from the network. Use only on trusted networks.", style="Warning.TLabel")
    # ... pack/grid and hide initially

    # UIの値をSettingsManagerにロード/セーブするロジックを実装
    # Comboboxの選択に応じて警告ラベルの表示/非表示を切り替える
    ```

---

## Step 5: テスト

全ての実装完了後、以下のテストを実施する。

1.  **デフォルト動作**: アプリケーションを起動し、APIサーバーが起動していないことを確認。
2.  **有効化**: 設定画面でAPIを有効化し、サーバーが起動することを確認。(`netstat` コマンド等)
3.  **APIキー生成**: APIキーが自動生成され、設定ファイルに保存されていることを確認。
4.  **APIアクセス (ローカル)**:
    - `curl` や `Postman` などのツールを使い、`127.0.0.1` に対して `GET` と `POST` をテストする。
    - APIキーなし、または不正なキーで `403 Forbidden` が返ることを確認。
5.  **APIアクセス (ネットワーク)**:
    - ホストを `0.0.0.0` に変更し、別のPCやスマートフォンからアクセスできることを確認。
6.  **設定変更の反映**: アプリケーション実行中にポート番号などを変更し、サーバーが新しい設定で再起動することを確認。
7.  **終了処理**: アプリケーション終了時に、サーバープロセスが正常に終了することを確認。

以上で、ネットワークAPI機能の実装は完了です。
