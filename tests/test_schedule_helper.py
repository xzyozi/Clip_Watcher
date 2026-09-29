"""tests/test_schedule_helper.py

ScheduleHelperComponent._select_date の時刻範囲バリデーションの単体テスト（#131）。

GUI 全体を構築せず、__init__ を回避して _select_date の実行に必要な属性だけを
注入した軽量インスタンス上でロジックを検証する。tk.StringVar の生成には
セッション共有の tk_root フィクスチャ（conftest.py）を用いる。
"""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime

from src.plugins.implementations.schedule_helper_plugin import ScheduleHelperComponent


def _make_component(
    tk_root: tk.Tk, hour_value: str, minute_value: str
) -> ScheduleHelperComponent:
    """__init__ を通さずに _select_date のテストに必要な属性だけを備えた
    ScheduleHelperComponent を生成する。"""
    component = ScheduleHelperComponent.__new__(ScheduleHelperComponent)
    component.logger = logging.getLogger("test_schedule_helper")
    component.today = datetime(2026, 1, 1, 9, 30)
    component.current_year = 2026
    component.current_month = 1
    component.selected_dates = []
    component.hour_var = tk.StringVar(master=tk_root, value=hour_value)
    component.minute_var = tk.StringVar(master=tk_root, value=minute_value)
    # _select_date 末尾で呼ばれる GUI 更新メソッドは副作用のため無効化する。
    component._update_calendar = lambda: None  # type: ignore[method-assign]
    component._update_text_widget = lambda *args: None  # type: ignore[method-assign]
    return component


def test_select_date_out_of_range_hour_falls_back_to_zero(tk_root: tk.Tk) -> None:
    """範囲外の hour（25）が 0 にフォールバックし、datetime.replace が
    ValueError を送出しないことを検証する（#131）。"""
    component = _make_component(tk_root, hour_value="25", minute_value="00")

    # 例外が送出されないこと
    component._select_date(15)

    assert len(component.selected_dates) == 1
    selected = component.selected_dates[0]
    assert selected.hour == 0
    assert selected.minute == 0
    assert (selected.year, selected.month, selected.day) == (2026, 1, 15)


def test_select_date_out_of_range_minute_falls_back_to_zero(tk_root: tk.Tk) -> None:
    """範囲外の minute（99）が 0 にフォールバックすることを検証する（#131）。"""
    component = _make_component(tk_root, hour_value="10", minute_value="99")

    component._select_date(10)

    assert len(component.selected_dates) == 1
    selected = component.selected_dates[0]
    assert selected.hour == 10
    assert selected.minute == 0


def test_select_date_negative_values_fall_back_to_zero(tk_root: tk.Tk) -> None:
    """負値の hour/minute が 0 にフォールバックすることを検証する（#131）。"""
    component = _make_component(tk_root, hour_value="-1", minute_value="-5")

    component._select_date(20)

    assert len(component.selected_dates) == 1
    selected = component.selected_dates[0]
    assert selected.hour == 0
    assert selected.minute == 0


def test_select_date_valid_values_are_preserved(tk_root: tk.Tk) -> None:
    """正当な hour/minute はそのまま保持されることを検証する（#131 の回帰防止）。"""
    component = _make_component(tk_root, hour_value="14", minute_value="45")

    component._select_date(5)

    assert len(component.selected_dates) == 1
    selected = component.selected_dates[0]
    assert selected.hour == 14
    assert selected.minute == 45
