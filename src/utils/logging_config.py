import logging
import os
import sys
from datetime import datetime


class DailyFileHandler(logging.FileHandler):
    """日付が変わったタイミングで自動的に新しいログファイルに切り替えるハンドラ。

    常時起動（日付を跨いで起動し続ける）した場合でも、ログファイル名の日付と
    実際に書き込まれるログメッセージのタイムスタンプの日付が一致するようにする。
    """

    def __init__(self, log_dir: str, encoding: str = 'utf-8') -> None:
        self.log_dir = log_dir
        self.encoding_ = encoding
        self.current_date = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(self.log_dir, f'clipwatcher_{self.current_date}.log')
        super().__init__(log_file, encoding=self.encoding_)

    def emit(self, record: logging.LogRecord) -> None:
        # ログ出力の直前に日付を確認し、日付が変わっていればファイルを切り替える
        new_date = datetime.now().strftime("%Y%m%d")
        if new_date != self.current_date:
            self.current_date = new_date
            self.close()  # 現在のファイルを閉じる
            self.baseFilename = os.path.abspath(
                os.path.join(self.log_dir, f'clipwatcher_{self.current_date}.log')
            )
            self.stream = self._open()
        super().emit(record)


def setup_logging() -> logging.Logger:
    """アプリケーション全体のロギング設定"""
    # ログディレクトリの設定
    if sys.platform == "win32":
        # USERPROFILEを使用して他のデータファイルと一貫性を保つ
        log_dir = os.path.join(os.environ['USERPROFILE'], '.clipWatcher', 'logs')
    else:
        log_dir = os.path.join(os.path.expanduser('~'), '.clipwatcher', 'logs')

    os.makedirs(log_dir, exist_ok=True)

    # 以前の実行で生成された空のログファイルをクリーンアップする
    try:
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(log_dir, filename)
                # ファイルが空かどうかを確認
                if os.path.getsize(file_path) == 0:
                    os.remove(file_path)
    except OSError as e:
        # ロガーが完全に設定される前なので、コンソールに出力する
        print(f"Error during log cleanup: {e}")


    # ログファイルの設定
    # 常時起動（日付を跨ぐ）してもファイル名の日付と実際のログのタイムスタンプが
    # ズレないように、日付が変わった最初のログ出力時に自動でファイルを切り替える
    # DailyFileHandler を使用する。従来の clipwatcher_YYYYMMDD.log という
    # ファイル名規則はそのまま維持される。
    file_handler = DailyFileHandler(log_dir, encoding='utf-8')

    # ロギングの基本設定
    # この関数が複数回呼び出された場合に備えて、既存のハンドラをクリアする
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            file_handler,
            logging.StreamHandler()
        ]
    )

    # ルートロガーの取得
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    return logger
