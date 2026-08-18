from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.hotkey.global_hotkey_listener import parse_hotkey_string

if TYPE_CHECKING:
    from src.core.hotkey.global_hotkey_listener import GlobalHotkeyListener

logger = logging.getLogger(__name__)


class HotkeyRegistrationManager:
    """ホットキーの登録状態・設定再構成を一元管理するマネージャ。

    競合判定と再登録、失敗時の復元処理を担当する。
    """

    def __init__(self, hotkey_listener: GlobalHotkeyListener) -> None:
        self._listener = hotkey_listener
        self._current_enabled: bool = False
        self._current_combo: str = ""

    @property
    def current_enabled(self) -> bool:
        return self._current_enabled

    @property
    def current_combo(self) -> str:
        return self._current_combo

    def reconfigure(self, enabled: bool, combo: str) -> bool:
        """候補設定を検証し、成功時だけ登録状態を切り替える。

        Returns:
            bool: 登録・再構成に成功した場合 True。失敗・競合した場合は False。
        """
        if self._current_enabled == enabled and self._current_combo == combo:
            logger.debug("ホットキー設定に変更がないため再構成をスキップします。")
            return True

        if not enabled:
            self._listener.stop()
            self._current_enabled = False
            self._current_combo = combo
            logger.info("グローバルホットキーを無効化しました。")
            return True

        try:
            modifiers, vk_code = parse_hotkey_string(combo)
        except ValueError as e:
            logger.warning("ホットキー文字列の解析エラー: %s", e)
            return False

        old_enabled = self._current_enabled
        old_combo = self._current_combo

        # 一旦現在のリスナーを停止
        self._listener.stop()

        # 新キーで登録試行
        success = self._listener.start(modifiers, vk_code)
        if success:
            self._current_enabled = True
            self._current_combo = combo
            logger.info("グローバルホットキーを登録しました: %s", combo)
            return True

        logger.warning("ホットキー %r の登録に失敗しました（キー競合等）。旧設定へ復元を試みます。", combo)
        # 復元試行
        if old_enabled and old_combo:
            try:
                old_mods, old_vk = parse_hotkey_string(old_combo)
                restored = self._listener.start(old_mods, old_vk)
                if restored:
                    self._current_enabled = True
                    self._current_combo = old_combo
                    logger.info("旧ホットキー %r に復元しました。", old_combo)
                else:
                    self._current_enabled = False
                    logger.error("旧ホットキー %r の復元にも失敗しました。", old_combo)
            except ValueError:
                self._current_enabled = False
        else:
            self._current_enabled = False

        return False

    def stop(self) -> None:
        """登録を解除してリスナーを停止する。"""
        self._listener.stop()
        self._current_enabled = False
