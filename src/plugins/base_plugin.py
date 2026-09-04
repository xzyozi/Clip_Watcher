from __future__ import annotations

from abc import ABC, abstractmethod


class Plugin(ABC):
    """すべてのプラグインに共通するGUI非依存の基底クラス。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """メニューや設定画面に表示するプラグイン名。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """プラグインの簡潔な説明。"""
        raise NotImplementedError


class TextPlugin(Plugin):
    """テキストを変換するGUI非依存プラグインの基底クラス。"""

    @abstractmethod
    def process(self, text: str) -> str:
        """入力テキストを変換して返す。"""
        raise NotImplementedError
