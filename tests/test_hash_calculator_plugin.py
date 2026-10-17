from __future__ import annotations

import hashlib
import tkinter as tk
from unittest.mock import MagicMock

from src.plugins.implementations.hash_calculator_plugin import (
    DEFAULT_SHAKE_DIGEST_LENGTH,
    MAX_HASH_INPUT_LENGTH,
    HashCalculatorComponent,
    HashCalculatorPlugin,
)


def test_hash_calculator_plugin_metadata() -> None:
    """HashCalculatorPlugin のメタデータと GUI コンポーネント生成を検証します。"""
    plugin = HashCalculatorPlugin()
    assert plugin.name == "Hash Calculator"
    assert plugin.has_gui_component() is True
    assert plugin.description != ""


def test_hash_calculator_combobox_readonly(tk_root: tk.Tk) -> None:
    """アルゴリズム選択用 Combobox が readonly で生成されることを検証します (#127)。"""
    mock_app = MagicMock()
    component = HashCalculatorComponent(tk_root, mock_app)

    # control_frame 内の Combobox を確認
    found_combo = False
    for child in component.winfo_children():
        for subchild in child.winfo_children():
            if isinstance(subchild, tk.ttk.Combobox):
                assert str(subchild.cget("state")) == "readonly"
                found_combo = True
    assert found_combo, "Combobox with state=readonly not found"


def test_hash_calculator_sha256(tk_root: tk.Tk) -> None:
    """SHA-256 ハッシュ計算が正常に行われることを検証します。"""
    mock_app = MagicMock()
    component = HashCalculatorComponent(tk_root, mock_app)

    component.algorithm_var.set("sha256")
    component.input_text.insert("1.0", "test input")
    component._calculate_hash()

    expected = hashlib.sha256(b"test input").hexdigest()
    output = component.output_text.get("1.0", "end-1c")
    assert output == expected


def test_hash_calculator_shake_xof_handling(tk_root: tk.Tk) -> None:
    """SHAKE-128 などの可変長出力関数（XOF）で TypeError にならずダイジェストが返ることを検証します (#127)。"""
    mock_app = MagicMock()
    component = HashCalculatorComponent(tk_root, mock_app)

    if "shake_128" in hashlib.algorithms_available:
        component.algorithm_var.set("shake_128")
        component.input_text.insert("1.0", "test shake")
        component._calculate_hash()

        expected = hashlib.shake_128(b"test shake").hexdigest(
            DEFAULT_SHAKE_DIGEST_LENGTH
        )
        output = component.output_text.get("1.0", "end-1c")
        assert output == expected


def test_hash_calculator_max_input_length_limit(tk_root: tk.Tk) -> None:
    """1MB を超える大容量入力で計算を中断し、DoS攻撃を防止することを検証します (#127)。"""
    mock_app = MagicMock()
    component = HashCalculatorComponent(tk_root, mock_app)

    # 1MB + 10 文字
    large_text = "a" * (MAX_HASH_INPUT_LENGTH + 10)
    component.input_text.insert("1.0", large_text)
    component._calculate_hash()

    output = component.output_text.get("1.0", "end-1c")
    assert "Error: Input text exceeds maximum allowed size" in output


def test_hash_calculator_debounce_on_text_change(
    tk_root: tk.Tk, mocker: MagicMock
) -> None:
    """テキスト変更時にデバウンスタイマーがスケジュールされることを検証します (#127)。"""
    mock_app = MagicMock()
    component = HashCalculatorComponent(tk_root, mock_app)

    # after をスパイ
    spy_after = mocker.spy(component, "after")
    component._on_text_change()

    assert spy_after.call_count == 1
    # 300ms デバウンス
    assert spy_after.call_args[0][0] == 300
    assert component._debounce_timer is not None

    # クリーンアップ
    component._cancel_debounce()
    assert component._debounce_timer is None
