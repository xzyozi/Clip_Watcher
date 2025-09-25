import logging
import os
import sys
from datetime import datetime

def setup_logging():
    """アプリケーション全体のロギング設定"""
    # ログディレクトリの設定
    if sys.platform == "win32":
        log_dir = os.path.join(os.environ['APPDATA'], 'ClipWatcher', 'logs')
    else:
        log_dir = os.path.join(os.path.expanduser('~'), '.clipwatcher', 'logs')

    os.makedirs(log_dir, exist_ok=True)

    # ログファイルの設定
    log_file = os.path.join(log_dir, f'clipwatcher_{datetime.now().strftime("%Y%m%d")}.log')

    # ロギングの基本設定
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

# グローバルロガーの設定
logger = setup_logging()
