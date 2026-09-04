"""組み込みプラグインの共通基底を提供するパッケージ。"""

from .base_plugin import Plugin, TextPlugin
from .gui_plugin import GuiPlugin

__all__ = [
    "Plugin",
    "TextPlugin",
    "GuiPlugin",
]
