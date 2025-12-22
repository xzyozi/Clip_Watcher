import logging
import os
import sys
from datetime import datetime

def setup_logging():
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
    log_file = os.path.join(log_dir, f'clipwatcher_{datetime.now().strftime("%Y%m%d")}.log')

    # ロギングの基本設定
    # この関数が複数回呼び出された場合に備えて、既存のハンドラをクリアする
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # ルートロガーの取得
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    return logger