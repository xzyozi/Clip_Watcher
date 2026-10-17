from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from io import TextIOWrapper

_DIR_MODE = 0o700
_FILE_MODE = 0o600


def _restrict_permissions(path: str, *, is_dir: bool) -> None:
    """ログディレクトリまたはログファイルのパーミッションを所有者のみに制限する。"""
    mode = _DIR_MODE if is_dir else _FILE_MODE
    try:
        os.chmod(path, mode)
    except OSError:
        # ファイルシステムやOS制約で変更できない場合でもロギング自体は継続する
        pass


def _cleanup_empty_logs(log_dir: str) -> None:
    """以前の実行で生成された空の通常ログファイルを安全に削除する。

    シンボリックリンクは追跡・削除せずスキップし、TOCTOU 競合による個別ファイルの
    OSError はファイル単位で捕捉して他のファイルの処理を継続する。
    """
    try:
        filenames = os.listdir(log_dir)
    except OSError as e:
        print(f"Error listing log directory: {e}")
        return

    for filename in filenames:
        if not filename.endswith(".log"):
            continue
        file_path = os.path.join(log_dir, filename)
        try:
            if os.path.islink(file_path):
                continue
            if os.path.isfile(file_path) and os.path.getsize(file_path) == 0:
                os.remove(file_path)
        except OSError as e:
            print(f"Error during log cleanup for {file_path}: {e}")


class DailyFileHandler(logging.FileHandler):
    """日付が変わったタイミングで自動的に新しいログファイルに切り替えるハンドラ。

    常時起動（日付を跨いで起動し続ける）した場合でも、ログファイル名の日付と
    実際に書き込まれるログメッセージのタイムスタンプの日付が一致するようにする。
    """

    def __init__(self, log_dir: str, encoding: str = "utf-8") -> None:
        self.log_dir = log_dir
        self.encoding_ = encoding
        self.current_date = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(self.log_dir, f"clipwatcher_{self.current_date}.log")
        super().__init__(log_file, encoding=self.encoding_)

    def _open(self) -> TextIOWrapper:
        stream = super()._open()
        _restrict_permissions(self.baseFilename, is_dir=False)
        return stream

    def emit(self, record: logging.LogRecord) -> None:
        # ログ出力の直前に日付を確認し、日付が変わっていればファイルを切り替える
        new_date = datetime.now().strftime("%Y%m%d")
        if new_date != self.current_date:
            self.current_date = new_date
            self.close()  # 現在のファイルを閉じる
            self.baseFilename = os.path.abspath(
                os.path.join(self.log_dir, f"clipwatcher_{self.current_date}.log")
            )
            self.stream = self._open()
        super().emit(record)


def setup_logging(log_dir: str | None = None) -> logging.Logger:
    """アプリケーション全体のロギング設定"""
    # ログディレクトリの設定
    if log_dir is None:
        if sys.platform == "win32":
            # USERPROFILEを使用して他のデータファイルと一貫性を保つ
            log_dir = os.path.join(os.environ["USERPROFILE"], ".clipWatcher", "logs")
        else:
            log_dir = os.path.join(os.path.expanduser("~"), ".clipwatcher", "logs")

    os.makedirs(log_dir, mode=_DIR_MODE, exist_ok=True)
    _restrict_permissions(log_dir, is_dir=True)

    # 以前の実行で生成された空のログファイルをクリーンアップする
    _cleanup_empty_logs(log_dir)

    # ログファイルの設定
    # 常時起動（日付を跨ぐ）してもファイル名の日付と実際のログのタイムスタンプが
    # ズレないように、日付が変わった最初のログ出力時に自動でファイルを切り替える
    # DailyFileHandler を使用する。従来の clipwatcher_YYYYMMDD.log という
    # ファイル名規則はそのまま維持される。
    file_handler = DailyFileHandler(log_dir, encoding="utf-8")

    # ロギングの基本設定
    # この関数が複数回呼び出された場合に備えて、既存のハンドラをクリアする
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[file_handler, logging.StreamHandler()],
    )

    # ルートロガーの取得
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    return logger
