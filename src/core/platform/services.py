"""src/core/platform/services.py

OS ごとの実装の選択を一元化する ``PlatformServices``。

どの OS でどの実装を使うかの判断はこのクラスに集約する。各クラスが
``sys.platform`` で分岐して自前でアダプターを生成することは行わない。
"""

from __future__ import annotations

import sys

from src.core.platform.errors import UnsupportedFeatureError
from src.core.platform.protocols import (
    PasteSender,
    ProcessInspector,
    SingleInstanceController,
    SoundPlayer,
)


class PlatformServices:
    """現在の OS で利用可能なプラットフォームアダプターを提供する。

    非対応の機能を取得しようとすると ``UnsupportedFeatureError`` を送出する。
    ``None`` や成功を装う Null 実装は返さない。

    テストではコンストラクタへモックを注入する（``sys.platform`` の差し替えは不要）。
    本番用は :meth:`for_current_platform` で生成する。
    """

    def __init__(
        self,
        *,
        process_inspector: ProcessInspector | None = None,
        sound_player: SoundPlayer | None = None,
        single_instance: SingleInstanceController | None = None,
        paste_sender: PasteSender | None = None,
        platform_name: str | None = None,
    ) -> None:
        self._process_inspector = process_inspector
        self._sound_player = sound_player
        self._single_instance = single_instance
        self._paste_sender = paste_sender
        self._platform_name = platform_name if platform_name else sys.platform

    @classmethod
    def for_current_platform(cls, platform_name: str | None = None) -> PlatformServices:
        """指定（省略時は現在）の OS 向けの実装を備えた PlatformServices を生成する。

        現在対応しているのは Windows のみ。他の OS ではアダプターを持たず、
        取得時に ``UnsupportedFeatureError`` となる。
        """
        name = platform_name if platform_name else sys.platform
        if name == "win32":
            from src.core.platform.windows import (
                WindowsPasteSender,
                WindowsProcessInspector,
                WindowsSingleInstanceController,
                WindowsSoundPlayer,
            )

            return cls(
                process_inspector=WindowsProcessInspector(),
                sound_player=WindowsSoundPlayer(),
                single_instance=WindowsSingleInstanceController(),
                paste_sender=WindowsPasteSender(),
                platform_name=name,
            )
        return cls(platform_name=name)

    def process_inspector(self) -> ProcessInspector:
        if self._process_inspector is None:
            raise UnsupportedFeatureError("process_inspector", self._platform_name)
        return self._process_inspector

    def sound_player(self) -> SoundPlayer:
        if self._sound_player is None:
            raise UnsupportedFeatureError("sound_player", self._platform_name)
        return self._sound_player

    def single_instance(self) -> SingleInstanceController:
        if self._single_instance is None:
            raise UnsupportedFeatureError("single_instance", self._platform_name)
        return self._single_instance

    def paste_sender(self) -> PasteSender:
        if self._paste_sender is None:
            raise UnsupportedFeatureError("paste_sender", self._platform_name)
        return self._paste_sender
