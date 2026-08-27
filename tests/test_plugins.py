from __future__ import annotations

from typing import Any

import pytest

from src.plugins.base_plugin import Plugin
from src.plugins.implementations.duplicate_line_remover_plugin import (
    DuplicateLineRemoverPlugin,
)
from src.plugins.implementations.html_escape_plugin import HTMLEscapePlugin
from src.plugins.implementations.line_sorter_plugin import LineSorterPlugin
from src.plugins.implementations.uppercase_converter_plugin import (
    UppercaseConverterPlugin,
)
from src.plugins.implementations.url_converter_plugin import URLConverterPlugin
from src.plugins.implementations.whitespace_normalizer_plugin import (
    WhitespaceNormalizerPlugin,
)
from src.plugins.manager import PluginManager

# ==========================================
# PluginManager Scan & Load Tests (3 Items)
# ==========================================


def test_plugin_manager_scan_and_load() -> None:
    """PluginManagerがロードを実行し、実装されたプラグインが検知されることを検証します。"""
    manager = PluginManager()
    plugins = manager.get_available_plugins()

    assert len(plugins) > 0
    # 組み込みの特定の代表的プラグインがロードされていること
    plugin_classes = [p.__class__.__name__ for p in plugins]
    assert "UppercaseConverterPlugin" in plugin_classes
    assert "URLConverterPlugin" in plugin_classes


def test_plugin_manager_broken_plugin_safety(mocker: Any) -> None:
    """モジュール読み込み時に例外が発生しても、他プラグインに影響せず処理が続行されることを検証します。"""
    # pkgutil.iter_modules の出力をモックし、正常なモジュール名と「壊れたモジュール名」を返させる
    mock_module_info = [
        (None, "src.plugins.implementations.uppercase_converter_plugin", False),
        (
            None,
            "src.plugins.implementations.broken_plugin_simulation",
            False,
        ),  # 存在しない・壊れたモジュール
    ]
    mocker.patch("pkgutil.iter_modules", return_value=mock_module_info)

    # ロード時に例外がログ記録され、正常に UppercaseConverterPlugin だけがロードされることを確認
    manager = PluginManager()
    plugins = manager.get_available_plugins()

    assert len(plugins) == 1
    assert isinstance(plugins[0], UppercaseConverterPlugin)


def test_gui_plugins_filtering() -> None:
    """GUIコンポーネントを持つプラグインのみが GUI プラグインリストに抽出されることを検証します。"""
    manager = PluginManager()

    gui_plugins = manager.get_gui_plugins()

    # GUIプラグインリストに含まれるものはすべて has_gui_component() が True であること
    for gp in gui_plugins:
        assert gp.has_gui_component() is True

    # 逆に、GUIを持たないプラグイン (例: UppercaseConverterPlugin) が含まれていないこと
    gui_classes = [gp.__class__.__name__ for gp in gui_plugins]
    assert "UppercaseConverterPlugin" not in gui_classes


# ==========================================
# Parameterized Text Conversion Tests (1 Item)
# ==========================================


@pytest.mark.parametrize(
    "plugin_class, input_text, expected_output",
    [
        # 1. 大文字変換
        (UppercaseConverterPlugin, "hello world", "HELLO WORLD"),
        (UppercaseConverterPlugin, "", ""),
        # 2. URLエンコード / デコード (URLConverterPlugin)
        # ※ URL変換プラグインのデフォルトの挙動（エンコードかデコードか）を検証
        (URLConverterPlugin, "hello world", "hello%20world"),
        (
            URLConverterPlugin,
            "hello%20world",
            "hello world",
        ),  # 再トグルでデコードされる仕様を検証
        # 3. 重複行削除 (DuplicateLineRemoverPlugin)
        (
            DuplicateLineRemoverPlugin,
            "line1\nline2\nline1\nline3",
            "line1\nline2\nline3",
        ),
        (DuplicateLineRemoverPlugin, "single", "single"),
        # 4. HTMLエスケープ (HTMLEscapePlugin)
        (HTMLEscapePlugin, "<div>&hello</div>", "&lt;div&gt;&amp;hello&lt;/div&gt;"),
        # 5. 行ソート (LineSorterPlugin)
        (LineSorterPlugin, "c\na\nb", "a\nb\nc"),
        # 6. 空白・改行正規化 (WhitespaceNormalizerPlugin)
        (WhitespaceNormalizerPlugin, "  hello   \n\n  world  ", "hello\n\nworld"),
    ],
)
def test_text_plugins_conversion(
    plugin_class: type[Plugin], input_text: str, expected_output: str
) -> None:
    """各テキスト変換プラグインが、ダミー値や極端な値に対して期待通り処理できるかを検証します。"""
    plugin = plugin_class()
    result = plugin.process(input_text)
    assert result == expected_output
