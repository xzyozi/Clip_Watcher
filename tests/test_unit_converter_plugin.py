from __future__ import annotations

import tkinter as tk
from unittest.mock import MagicMock

from src.plugins.implementations.unit_converter_plugin import (
    MAX_CONVERTER_INPUT_LENGTH,
    UnitConverterComponent,
    UnitConverterPlugin,
)


def test_unit_converter_plugin_metadata() -> None:
    """プラグインの基本情報とGUIフラグを検証します。"""
    plugin = UnitConverterPlugin()
    assert plugin.name == "Unit Converter"
    assert plugin.has_gui_component() is True
    assert plugin.description != ""


def test_unit_converter_component_initialization(tk_root: tk.Tk) -> None:
    """コンポーネント初期化時に各コンボボックスが readonly で生成されることを検証します (#129)。"""
    mock_app = MagicMock()
    component = UnitConverterComponent(tk_root, mock_app)

    # category_combo, from_unit_combo, to_unit_combo の state を検証
    assert str(component.from_unit_combo.cget("state")) == "readonly"
    assert str(component.to_unit_combo.cget("state")) == "readonly"


def test_unit_converter_length_conversion(tk_root: tk.Tk) -> None:
    """長さ変換（Meter -> Centimeter）が正しく機能することを検証します。"""
    mock_app = MagicMock()
    component = UnitConverterComponent(tk_root, mock_app)

    component.category_var.set("Length")
    component._on_category_change()
    component.from_unit_var.set("Meter")
    component.to_unit_var.set("Centimeter")
    component.input_var.set("1.5")
    component._convert()

    assert component.output_var.get() == "Result: 150.0000"


def test_unit_converter_temperature_conversion(tk_root: tk.Tk) -> None:
    """温度変換（Celsius -> Fahrenheit）が正しく機能することを検証します。"""
    mock_app = MagicMock()
    component = UnitConverterComponent(tk_root, mock_app)

    component.category_var.set("Temperature")
    component._on_category_change()
    component.from_unit_var.set("Celsius")
    component.to_unit_var.set("Fahrenheit")
    component.input_var.set("100")
    component._convert()

    assert component.output_var.get() == "Result: 212.0000"


def test_unit_converter_time_conversion_valid(tk_root: tk.Tk) -> None:
    """有効なUnixタイムスタンプから日時文字列への変換を検証します。"""
    mock_app = MagicMock()
    component = UnitConverterComponent(tk_root, mock_app)

    component.category_var.set("Time")
    component._on_category_change()
    component.from_unit_var.set("Unix Timestamp")
    component.to_unit_var.set("Datetime String")
    component.input_var.set("0")
    component._convert()

    # UTC/ローカル時刻によらず、正常に日付形式の文字列が得られること
    result = component.output_var.get()
    assert result.startswith("Result: 1970-")


def test_unit_converter_time_conversion_out_of_range(tk_root: tk.Tk) -> None:
    """負のタイムスタンプやミリ秒エポック、極大値でクラッシュせず Result: Error になることを検証します (#129)。"""
    mock_app = MagicMock()
    component = UnitConverterComponent(tk_root, mock_app)

    component.category_var.set("Time")
    component._on_category_change()
    component.from_unit_var.set("Unix Timestamp")
    component.to_unit_var.set("Datetime String")

    # 1. 負のタイムスタンプ
    component.input_var.set("-100")
    component._convert()
    assert component.output_var.get() == "Result: Error"

    # 2. ミリ秒タイムスタンプ（13桁）
    component.input_var.set("1700000000000")
    component._convert()
    assert component.output_var.get() == "Result: Error"

    # 3. 極大値
    component.input_var.set("1e30")
    component._convert()
    assert component.output_var.get() == "Result: Error"


def test_unit_converter_input_length_limit(tk_root: tk.Tk) -> None:
    """極端に長い入力文字列（DoS攻撃対策）で処理を早期遮断することを検証します (#129)。"""
    mock_app = MagicMock()
    component = UnitConverterComponent(tk_root, mock_app)

    component.category_var.set("Length")
    component._on_category_change()
    component.input_var.set("1" * (MAX_CONVERTER_INPUT_LENGTH + 10))
    component._convert()

    assert component.output_var.get() == "Result: Input too long"


def test_unit_converter_invalid_numeric_input(tk_root: tk.Tk) -> None:
    """数値としてパースできない文字列で Result: Invalid number になることを検証します。"""
    mock_app = MagicMock()
    component = UnitConverterComponent(tk_root, mock_app)

    component.category_var.set("Length")
    component._on_category_change()
    component.input_var.set("not-a-number")
    component._convert()

    assert component.output_var.get() == "Result: Invalid number"
