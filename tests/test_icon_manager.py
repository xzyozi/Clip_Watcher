from __future__ import annotations

import string
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st
from PIL import Image

from src.core.config.defaults import THEMES
from src.gui.icon_manager import IconManager


def test_icon_manager_initializes_empty_caches_with_configured_icons_directory() -> None:
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
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(icons_dir / "pin.png")
    monkeypatch.setattr(
        "src.gui.icon_manager.ImageTk.PhotoImage", lambda image: object()
    )
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
        Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(
            icons_dir / f"{icon_name}.png"
        )

        with patch(
            "src.gui.icon_manager.ImageTk.PhotoImage", side_effect=lambda image: object()
        ):
            manager = IconManager(icons_dir=str(icons_dir))
            first_icon = manager.get_icon(icon_name, theme_name)
            repeated_icons = [
                manager.get_icon(icon_name, theme_name)
                for _ in range(call_count - 1)
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

    with (
        patch("src.gui.icon_manager.Image.open") as image_open,
        patch(
            "src.gui.icon_manager.ImageTk.PhotoImage",
            side_effect=lambda image: object(),
        ),
    ):
        image_open.return_value.__enter__.return_value = Image.new(
            "RGBA", (1, 1), (255, 0, 0, 255)
        )
        manager = IconManager(icons_dir="test-assets/icons")

        assert manager._source_images == {}
        for theme_name in theme_names:
            manager.get_icon(icon_name, theme_name)

    assert image_open.call_count == 1
    assert set(manager._source_images) == {icon_name}


def test_get_icon_reuses_loaded_source_when_requesting_another_theme(
    tmp_path, monkeypatch
) -> None:
    """要件2.4: テーマが異なっても元画像の再読込なしで表示画像を生成する。"""
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    icon_path = icons_dir / "pin.png"
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(icon_path)
    monkeypatch.setattr(
        "src.gui.icon_manager.ImageTk.PhotoImage", lambda image: object()
    )
    manager = IconManager(icons_dir=str(icons_dir))

    first_icon = manager.get_icon("pin", "light")
    icon_path.unlink()
    second_icon = manager.get_icon("pin", "dark")

    assert second_icon is not first_icon
    assert set(manager._source_images) == {"pin"}
    assert set(manager._icon_cache) == {"pin:light", "pin:dark"}


@pytest.mark.parametrize("theme_name", ["light", "dark"])
def test_get_icon_uses_the_theme_listbox_foreground_color(
    tmp_path, theme_name, monkeypatch
) -> None:
    """要件3.1: PhotoImage生成時のRGBA画像がテーマ前景色で着色される。"""
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(icons_dir / "pin.png")
    photo_image_inputs: list[Image.Image] = []

    def capture_photo_image(image: Image.Image) -> object:
        photo_image_inputs.append(image.copy())
        return object()

    monkeypatch.setattr(
        "src.gui.icon_manager.ImageTk.PhotoImage", capture_photo_image
    )

    manager = IconManager(icons_dir=str(icons_dir))
    icon = manager.get_icon("pin", theme_name)
    color = THEMES[theme_name]["listbox_fg"]
    expected_rgb = tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))

    assert len(photo_image_inputs) == 1
    assert photo_image_inputs[0].mode == "RGBA"
    assert photo_image_inputs[0].getpixel((0, 0)) == (*expected_rgb, 255)
    assert icon is manager.get_icon("pin", theme_name)


def test_apply_theme_color_replaces_rgb_and_preserves_alpha() -> None:
    """要件3.1・3.3: 色変換後も各ピクセルのアルファ値を維持する。"""
    source = Image.new("RGBA", (2, 2))
    source.putdata(
        [
            (255, 0, 0, 0),
            (0, 255, 0, 64),
            (0, 0, 255, 128),
            (255, 255, 255, 255),
        ]
    )
    manager = IconManager()

    colored_image = manager._apply_theme_color(source, "#123456")

    assert colored_image.mode == "RGBA"
    assert colored_image.size == source.size
    assert list(colored_image.get_flattened_data()) == [
        (18, 52, 86, 0),
        (18, 52, 86, 64),
        (18, 52, 86, 128),
        (18, 52, 86, 255),
    ]


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
    manager._source_images = {
        icon_name: Image.new("RGBA", (1, 1), (255, 0, 0, 255))
        for icon_name in icon_names
    }

    with patch(
        "src.gui.icon_manager.ImageTk.PhotoImage", side_effect=lambda image: object()
    ):
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
        Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(
            icons_dir / f"{icon_name}.png"
        )

        with (
            patch("src.gui.icon_manager.Image.open", wraps=Image.open) as image_open,
            patch(
                "src.gui.icon_manager.ImageTk.PhotoImage",
                side_effect=lambda image: object(),
            ) as photo_image,
        ):
            manager = IconManager(icons_dir=str(icons_dir))
            first_icon = manager.get_icon(icon_name, theme_name)
            source_image = manager._source_images[icon_name]

            manager.invalidate_theme(theme_name)
            regenerated_icon = manager.get_icon(icon_name, theme_name)

    assert regenerated_icon is not first_icon
    assert manager._source_images[icon_name] is source_image
    assert image_open.call_count == 1
    assert photo_image.call_count == 2
