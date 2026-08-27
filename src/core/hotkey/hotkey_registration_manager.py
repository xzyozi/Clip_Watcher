from __future__ import annotations

import logging
from collections.abc import Mapping

from src.core.hotkey.global_hotkey_listener import (
    GLOBAL_HOTKEY_ID,
    GlobalHotkeyListener,
    HotkeyRegistration,
    format_hotkey,
    parse_hotkey_string,
)

logger = logging.getLogger(__name__)

_PINNED_HOTKEY_ID_START = GLOBAL_HOTKEY_ID + 1


def normalize_pinned_hotkey_bindings(value: object) -> dict[int, str]:
    """JSON由来の割当を検証し、履歴IDから正規化済みキー文字列への辞書へ変換する。"""
    if not isinstance(value, Mapping):
        return {}

    normalized: dict[int, str] = {}
    for raw_history_id, raw_combo in value.items():
        try:
            history_id = int(raw_history_id)
        except (TypeError, ValueError):
            continue
        if history_id <= 0 or not isinstance(raw_combo, str):
            continue
        try:
            modifiers, vk_code = parse_hotkey_string(raw_combo)
        except ValueError:
            continue
        normalized[history_id] = format_hotkey(modifiers, vk_code)
    return normalized


class HotkeyRegistrationManager:
    """ホットキー登録集合の検証・置換・失敗時復元を一元管理する。"""

    def __init__(self, hotkey_listener: GlobalHotkeyListener) -> None:
        self._listener = hotkey_listener
        self._global_enabled = False
        self._global_combo = ""
        self._pinned_bindings: dict[int, str] = {}
        self._hotkey_to_history: dict[int, int] = {}

    @property
    def current_enabled(self) -> bool:
        """互換性のため、表示/最小化キーの有効状態を返す。"""
        return self._global_enabled

    @property
    def current_combo(self) -> str:
        """互換性のため、表示/最小化キーのキー文字列を返す。"""
        return self._global_combo

    @property
    def pinned_bindings(self) -> dict[int, str]:
        return self._pinned_bindings.copy()

    def history_id_for_hotkey(self, hotkey_id: int) -> int | None:
        return self._hotkey_to_history.get(hotkey_id)

    def reconfigure(self, enabled: bool, combo: str) -> bool:
        """従来の表示/最小化キーだけを再構成する Interface。"""
        return self.reconfigure_all(enabled, combo, self._pinned_bindings)

    def reconfigure_all(
        self,
        global_enabled: bool,
        global_combo: str,
        pinned_bindings: Mapping[int, str],
    ) -> bool:
        """候補の登録集合を原子的に適用し、失敗時は旧集合を復元する。"""
        normalized = normalize_pinned_hotkey_bindings(pinned_bindings)
        try:
            registrations, hotkey_to_history, canonical_global_combo = (
                self._build_registrations(global_enabled, global_combo, normalized)
            )
        except ValueError as error:
            logger.warning("ホットキー設定の検証に失敗しました: %s", error)
            return False

        unchanged = (
            self._global_enabled == global_enabled
            and self._global_combo == canonical_global_combo
            and self._pinned_bindings == normalized
        )
        if unchanged:
            return True

        old_global_enabled = self._global_enabled
        old_global_combo = self._global_combo
        old_pinned_bindings = self._pinned_bindings.copy()
        old_hotkey_to_history = self._hotkey_to_history.copy()

        if self._activate_registrations(registrations):
            self._global_enabled = global_enabled
            self._global_combo = canonical_global_combo
            self._pinned_bindings = normalized
            self._hotkey_to_history = hotkey_to_history
            logger.info("ホットキー登録集合を更新しました: %d 件", len(registrations))
            return True

        logger.warning("ホットキー登録集合の更新に失敗しました。旧設定を復元します。")
        old_registrations, _, _ = self._build_registrations(
            old_global_enabled, old_global_combo, old_pinned_bindings
        )
        self._activate_registrations(old_registrations)
        self._global_enabled = old_global_enabled
        self._global_combo = old_global_combo
        self._pinned_bindings = old_pinned_bindings
        self._hotkey_to_history = old_hotkey_to_history
        return False

    def _activate_registrations(self, registrations: list[HotkeyRegistration]) -> bool:
        """単一の従来キーは既存 Interface、それ以外は集合 Interface を使用する。"""
        if not registrations:
            self._listener.stop()
            return True
        if len(registrations) == 1 and registrations[0].hotkey_id == GLOBAL_HOTKEY_ID:
            entry = registrations[0]
            return self._listener.start(entry.modifiers, entry.vk_code)
        return self._listener.start_many(registrations)

    def stop(self) -> None:
        """登録済みの全ホットキーを解除する。"""
        self._listener.stop()
        self._global_enabled = False
        self._hotkey_to_history.clear()

    def _build_registrations(
        self,
        global_enabled: bool,
        global_combo: str,
        pinned_bindings: Mapping[int, str],
    ) -> tuple[list[HotkeyRegistration], dict[int, int], str]:
        registrations: list[HotkeyRegistration] = []
        hotkey_to_history: dict[int, int] = {}
        used_combos: set[str] = set()
        canonical_global_combo = global_combo

        if global_enabled:
            modifiers, vk_code = parse_hotkey_string(global_combo)
            canonical_global_combo = format_hotkey(modifiers, vk_code)
            used_combos.add(canonical_global_combo)
            registrations.append(
                HotkeyRegistration(GLOBAL_HOTKEY_ID, modifiers, vk_code)
            )

        for offset, (history_id, combo) in enumerate(sorted(pinned_bindings.items())):
            modifiers, vk_code = parse_hotkey_string(combo)
            canonical_combo = format_hotkey(modifiers, vk_code)
            if canonical_combo in used_combos:
                raise ValueError(f"ホットキーが重複しています: {canonical_combo}")
            used_combos.add(canonical_combo)
            hotkey_id = _PINNED_HOTKEY_ID_START + offset
            registrations.append(HotkeyRegistration(hotkey_id, modifiers, vk_code))
            hotkey_to_history[hotkey_id] = history_id

        return registrations, hotkey_to_history, canonical_global_combo
