"""PNGアイコンの元画像と表示用画像を管理する基盤。"""

import os
import tkinter as tk

from PIL import Image, ImageTk

from src.core.config.defaults import THEMES


class IconManager:
    """アイコン画像の元データとテーマ別表示画像のキャッシュを保持する。"""

    def __init__(self, icons_dir: str = "assets/icons") -> None:
        """アイコン画像のキャッシュを空の状態で初期化する。

        Args:
            icons_dir: アイコンPNGファイルを格納するディレクトリ。
        """
        self._icons_dir = icons_dir
        self._source_images: dict[str, Image.Image] = {}
        self._icon_cache: dict[str, tk.PhotoImage] = {}

    @staticmethod
    def _cache_key(icon_name: str, theme_name: str) -> str:
        """アイコン名とテーマ名からテーマ別キャッシュキーを生成する。"""
        return f"{icon_name}:{theme_name}"

    def _apply_theme_color(
        self, source: Image.Image, target_color_hex: str
    ) -> Image.Image:
        """RGBA画像のアルファを維持し、RGBを指定のテーマ色に置き換える。"""
        colored_image = Image.new("RGBA", source.size, target_color_hex)
        colored_image.putalpha(source.getchannel("A"))
        return colored_image

    def get_icon(self, icon_name: str, theme_name: str) -> tk.PhotoImage:
        """アイコンを取得し、テーマ前景色で変換した表示画像をキャッシュする。"""
        key = self._cache_key(icon_name, theme_name)
        if key in self._icon_cache:
            return self._icon_cache[key]

        if icon_name not in self._source_images:
            icon_path = os.path.join(self._icons_dir, f"{icon_name}.png")
            with Image.open(icon_path) as image:
                self._source_images[icon_name] = image.convert("RGBA")

        colored_image = self._apply_theme_color(
            self._source_images[icon_name], THEMES[theme_name]["listbox_fg"]
        )
        photo_image = ImageTk.PhotoImage(colored_image)
        self._icon_cache[key] = photo_image
        return photo_image

    def invalidate_theme(self, theme_name: str) -> None:
        """指定テーマの表示画像キャッシュを破棄する。"""
        suffix = f":{theme_name}"
        stale_keys = [key for key in self._icon_cache if key.endswith(suffix)]
        for key in stale_keys:
            del self._icon_cache[key]

    def has_icon_source(self, icon_name: str) -> bool:
        """指定アイコンのPNG元画像が存在するかを読み込まずに確認する。"""
        return os.path.isfile(os.path.join(self._icons_dir, f"{icon_name}.png"))
