"""PNGアイコンの元画像と表示用画像を管理する基盤。"""

from __future__ import annotations

import os
from tkinter import PhotoImage

# src/gui/icon_manager.py -> リポジトリルート/assets/icons
DEFAULT_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets",
    "icons",
)


class IconManager:
    """アイコン画像の元データとテーマ別表示画像のキャッシュを保持する。"""

    def __init__(self, icons_dir: str | None = None) -> None:
        """アイコン画像のキャッシュを空の状態で初期化する。

        Args:
            icons_dir: アイコンPNGファイルを格納するディレクトリ。
                未指定の場合は、カレントディレクトリに依存しない
                リポジトリ内の ``assets/icons`` の絶対パスを使う。
        """
        self._icons_dir = DEFAULT_ICONS_DIR if icons_dir is None else icons_dir
        self._source_images: dict[str, PhotoImage] = {}
        self._icon_cache: dict[str, PhotoImage] = {}
        # 表示画像を破棄するたびに増える世代番号。Treeview 等は画像を名前で
        # 参照するため、破棄後は利用側が画像を再設定する必要がある。
        self.cache_generation: int = 0

    @staticmethod
    def _cache_key(icon_name: str, theme_name: str) -> str:
        """アイコン名とテーマ名からテーマ別キャッシュキーを生成する。"""
        return f"{icon_name}:{theme_name}"

    def get_icon(self, icon_name: str, theme_name: str) -> PhotoImage:
        """アイコン本来のRGBA色を保持した表示画像をキャッシュする。"""
        key = self._cache_key(icon_name, theme_name)
        if key in self._icon_cache:
            return self._icon_cache[key]

        if icon_name not in self._source_images:
            icon_path = os.path.join(self._icons_dir, f"{icon_name}.png")
            self._source_images[icon_name] = PhotoImage(file=icon_path)

        photo_image = self._source_images[icon_name].copy()
        self._icon_cache[key] = photo_image
        return photo_image

    def invalidate_theme(self, theme_name: str) -> None:
        """指定テーマの表示画像キャッシュを破棄する。"""
        suffix = f":{theme_name}"
        stale_keys = [key for key in self._icon_cache if key.endswith(suffix)]
        for key in stale_keys:
            del self._icon_cache[key]
        if stale_keys:
            self.cache_generation += 1

    def has_icon_source(self, icon_name: str) -> bool:
        """指定アイコンのPNG元画像が存在するかを読み込まずに確認する。"""
        return os.path.isfile(os.path.join(self._icons_dir, f"{icon_name}.png"))
