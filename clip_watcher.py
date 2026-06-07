import os
import sys

from src.event_handlers import start_app

# プロジェクトのルートディレクトリを特定し、sys.pathに追加
# これは、他のモジュールが絶対パスでインポートされることを可能にする
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
sys.path.insert(0, project_root)


if __name__ == "__main__":
    start_app()
