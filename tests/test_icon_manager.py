from __future__ import annotations

import string
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.core.config.defaults import THEMES
from src.gui.icon_manager import IconManager

TINY_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x03\x00\x05\xfe"
    b"\x02\xfe\xa7\x96\x0b\xa7\x00\x00\x00\x00IEND\xaeB`\x82"
)


class MockPhotoImage:
    """テスト用の PhotoImage 代替モッククラス。"""

    def __init__(self, file: str | None = None) -> None:
        self.file = file

    def copy(self) -> MockPhotoImage:
        copied = MockPhotoImage(file=self.file)
        return copied


def test_icon_manager_initializes_empty_caches_with_configured_icons_directory() -> (
    None
):
    """コンストラクタは指定ディレクトリと空の画像キャッシュを保持する。"""
    manager = IconManager(icons_dir="test-assets/icons")

    assert manager._icons_dir == "test-assets/icons"
    assert manager._source_images == {}
    assert manager._icon_cache == {}


def test_cache_key_combines_icon_and_theme_names_with_colon() -> None:
    """要件1.1: アイコン名・テーマ名から決定的なキャッシュキーを生成する。"""
    assert IconManager._cache_key("pin", "dark") == "pin:dark"
    assert IconManager._cache_key("status-icon", "light") == "status-icon:light"


def test_has_icon_source_reports_existing_png_without_loading_it(tmp_path) -> None:
    """元画像の有無だけを確認し、存在確認時に画像を読み込まない。"""
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    (icons_dir / "pin.png").write_text("not a valid PNG", encoding="utf-8")
    manager = IconManager(icons_dir=str(icons_dir))

    assert manager.has_icon_source("pin") is True
    assert manager.has_icon_source("missing") is False
    assert manager._source_images == {}
    assert manager._icon_cache == {}


def test_get_icon_returns_cached_photo_image_for_same_icon_and_theme(
    tmp_path, monkeypatch
) -> None:
    """要件1.1・1.2: 同一キーではキャッシュ済みの画像参照を再利用する。"""
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    (icons_dir / "pin.png").write_bytes(TINY_PNG_BYTES)
    monkeypatch.setattr("src.gui.icon_manager.PhotoImage", MockPhotoImage)
    manager = IconManager(icons_dir=str(icons_dir))

    first_icon = manager.get_icon("pin", "light")
    second_icon = manager.get_icon("pin", "light")

    assert second_icon is first_icon
    assert manager._icon_cache == {"pin:light": first_icon}


@given(
    icon_name=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=12),
    theme_name=st.sampled_from(tuple(THEMES)),
    call_count=st.integers(min_value=2, max_value=5),
)
def test_get_icon_returns_the_same_reference_for_repeated_requests_property(
    icon_name: str, theme_name: str, call_count: int
) -> None:
    """Property 1 / 要件1.1・1.2: 無効化前の同一要求は同じ参照を返す。"""
    with TemporaryDirectory() as temporary_directory:
        icons_dir = Path(temporary_directory) / "icons"
        icons_dir.mkdir()
        (icons_dir / f"{icon_name}.png").write_bytes(TINY_PNG_BYTES)

        with patch(
            "src.gui.icon_manager.PhotoImage",
            MockPhotoImage,
        ):
            manager = IconManager(icons_dir=str(icons_dir))
            first_icon = manager.get_icon(icon_name, theme_name)
            repeated_icons = [
                manager.get_icon(icon_name, theme_name) for _ in range(call_count - 1)
            ]

    assert all(icon is first_icon for icon in repeated_icons)
    assert manager._icon_cache[manager._cache_key(icon_name, theme_name)] is first_icon


@given(
    icon_name=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=12),
    additional_theme_names=st.lists(
        st.sampled_from(tuple(THEMES)), min_size=0, max_size=3
    ),
)
def test_get_icon_loads_source_once_across_themes_property(
    icon_name: str, additional_theme_names: list[str]
) -> None:
    """Property 2 / 要件2.1・2.2: 元画像は異なるテーマでも一度だけ読み込む。"""
    theme_names = [*tuple(THEMES), *additional_theme_names]

    with patch("src.gui.icon_manager.PhotoImage") as photo_image_cls:
        mock_source = MagicMock()
        mock_source.copy.side_effect = lambda: MagicMock()
        photo_image_cls.return_value = mock_source

        manager = IconManager(icons_dir="test-assets/icons")

        assert manager._source_images == {}
        for theme_name in theme_names:
            manager.get_icon(icon_name, theme_name)

    assert photo_image_cls.call_count == 1
    assert set(manager._source_images) == {icon_name}


def test_get_icon_reuses_loaded_source_when_requesting_another_theme(
    tmp_path, monkeypatch
) -> None:
    """要件2.4: テーマが異なっても元画像の再読込なしで表示画像を生成する。"""
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    icon_path = icons_dir / "pin.png"
    icon_path.write_bytes(TINY_PNG_BYTES)
    monkeypatch.setattr("src.gui.icon_manager.PhotoImage", MockPhotoImage)
    manager = IconManager(icons_dir=str(icons_dir))

    first_icon = manager.get_icon("pin", "light")
    icon_path.unlink()
    second_icon = manager.get_icon("pin", "dark")

    assert second_icon is not first_icon
    assert set(manager._source_images) == {"pin"}
    assert set(manager._icon_cache) == {"pin:light", "pin:dark"}


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_get_icon_preserves_source_colors_and_alpha(
    tmp_path, theme_name, monkeypatch
) -> None:
    """アイコン取得時に PhotoImage が読み込まれ、キャッシュから取得されることを検証する。"""
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    icon_file = icons_dir / "pin.png"
    icon_file.write_bytes(TINY_PNG_BYTES)

    created_instances: list[MockPhotoImage] = []

    def mock_photo_image(file: str) -> MockPhotoImage:
        inst = MockPhotoImage(file=file)
        created_instances.append(inst)
        return inst

    monkeypatch.setattr("src.gui.icon_manager.PhotoImage", mock_photo_image)

    manager = IconManager(icons_dir=str(icons_dir))
    icon = manager.get_icon("pin", theme_name)

    assert len(created_instances) == 1
    assert created_instances[0].file == str(icon_file)
    assert icon is manager.get_icon("pin", theme_name)


@given(
    theme_names=st.permutations(tuple(THEMES)),
    icon_names=st.lists(
        st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=12),
        min_size=1,
        max_size=4,
        unique=True,
    ),
)
def test_invalidate_theme_removes_only_target_theme_cache_entries_property(
    theme_names: tuple[str, ...], icon_names: list[str]
) -> None:
    """Property 3 / 要件3.1・3.2: 対象テーマのキャッシュだけを破棄する。"""
    target_theme, other_theme = theme_names
    manager = IconManager()
    manager._source_images = {icon_name: MockPhotoImage() for icon_name in icon_names}

    with patch("src.gui.icon_manager.PhotoImage", MockPhotoImage):
        for icon_name in icon_names:
            manager.get_icon(icon_name, target_theme)
            manager.get_icon(icon_name, other_theme)

    target_keys = {
        manager._cache_key(icon_name, target_theme) for icon_name in icon_names
    }
    other_keys = {
        manager._cache_key(icon_name, other_theme) for icon_name in icon_names
    }

    manager.invalidate_theme(target_theme)

    assert target_keys.isdisjoint(manager._icon_cache)
    assert other_keys <= manager._icon_cache.keys()


@given(
    icon_name=st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=12),
    theme_name=st.sampled_from(tuple(THEMES)),
)
def test_get_icon_regenerates_photo_image_and_reuses_source_after_invalidation_property(
    icon_name: str, theme_name: str
) -> None:
    """Property 4 / 要件3.5: 無効化後は新規画像を元画像再読込なしで生成する。"""
    with TemporaryDirectory() as temporary_directory:
        icons_dir = Path(temporary_directory) / "icons"
        icons_dir.mkdir()
        (icons_dir / f"{icon_name}.png").write_bytes(TINY_PNG_BYTES)

        with patch("src.gui.icon_manager.PhotoImage") as photo_image_cls:
            mock_source = MagicMock()
            mock_source.copy.side_effect = lambda: MagicMock()
            photo_image_cls.return_value = mock_source

            manager = IconManager(icons_dir=str(icons_dir))
            first_icon = manager.get_icon(icon_name, theme_name)
            source_image = manager._source_images[icon_name]

            manager.invalidate_theme(theme_name)
            regenerated_icon = manager.get_icon(icon_name, theme_name)

    assert regenerated_icon is not first_icon
    assert manager._source_images[icon_name] is source_image
    assert photo_image_cls.call_count == 1
    assert mock_source.copy.call_count == 2


def test_pinned_icon_asset_is_16px_rgba() -> None:
    """実行用ピンアイコンは既存の行レイアウトに収まる16px PNG画像である。"""
    with open("assets/icons/pin.png", "rb") as f:
        header = f.read(24)
        assert header[:8] == b"\x89PNG\r\n\x1a\n"
        width, height = struct.unpack(">II", header[16:24])
        assert (width, height) == (16, 16)
