import os
import sys

# Add the project root to the Python path
# This is necessary to ensure that imports like `from src.core...` work correctly
# when running this script as the main entry point.
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.event_handlers import start_app

if __name__ == "__main__":
    start_app()