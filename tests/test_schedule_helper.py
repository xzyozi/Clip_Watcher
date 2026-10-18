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


def test_calendar_weekday_headers_align_with_dates_sunday_first(
    tk_root: tk.Tk,
) -> None:
    """日曜日始まり（SUNDAY）でヘッダー曜日と日付列の曜日が完全に一致することを検証する。"""
    import calendar
    from tkinter import ttk

    component = ScheduleHelperComponent.__new__(ScheduleHelperComponent)
    component.logger = logging.getLogger("test_schedule_helper")
    component.today = datetime(2026, 10, 18, 12, 0)
    component.current_year = 2026
    component.current_month = 10
    component.selected_dates = []

    mock_app = type("App", (), {})()
    ja_days = ["日", "月", "火", "水", "木", "金", "土"]
    mock_app.translator = lambda key: ja_days if key == "days_short" else key  # type: ignore[attr-defined]
    component.app = mock_app  # type: ignore[assignment]

    frame = ttk.Frame(tk_root)
    component.calendar_frame = frame
    component.month_year_label = ttk.Label(tk_root)

    calendar.setfirstweekday(calendar.SUNDAY)
    component._update_calendar()

    # row=0 のヘッダーラベルを取得
    header_labels: dict[int, str] = {}
    date_buttons: list[tuple[int, int, int]] = []  # (row, col, day_number)

    for child in frame.winfo_children():
        info = child.grid_info()
        row = int(info["row"])
        col = int(info["column"])
        if row == 0:
            header_labels[col] = child.cget("text")
        else:
            date_buttons.append((row, col, int(child.cget("text"))))

    # 日曜日始まりなのでヘッダーは 日, 月, 火, 水, 木, 金, 土
    assert [header_labels[c] for c in range(7)] == ja_days

    # 各日付ボタンの曜日（datetime.weekday()）と列ヘッダーが完全一致すること
    # Python の weekday: 0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日
    weekday_to_ja = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
    assert len(date_buttons) == 31
    for _r, col, day in date_buttons:
        dt = datetime(2026, 10, day)
        expected_label = weekday_to_ja[dt.weekday()]
        assert header_labels[col] == expected_label, (
            f"Day {day} ({expected_label}) is placed in column {col} with header {header_labels[col]}"
        )

    # 2026-10-18（日曜日）は column 0 に配置されていること
    oct_18_col = next(col for _r, col, day in date_buttons if day == 18)
    assert oct_18_col == 0
    assert header_labels[oct_18_col] == "日"

    frame.destroy()


def test_calendar_weekday_headers_align_with_dates_monday_first(
    tk_root: tk.Tk,
) -> None:
    """月曜日始まり（MONDAY）でもヘッダー曜日が回転し日付列の曜日と完全に一致することを検証する。"""
    import calendar
    from tkinter import ttk

    component = ScheduleHelperComponent.__new__(ScheduleHelperComponent)
    component.logger = logging.getLogger("test_schedule_helper")
    component.today = datetime(2026, 10, 18, 12, 0)
    component.current_year = 2026
    component.current_month = 10
    component.selected_dates = []

    mock_app = type("App", (), {})()
    ja_days = ["日", "月", "火", "水", "木", "金", "土"]
    mock_app.translator = lambda key: ja_days if key == "days_short" else key  # type: ignore[attr-defined]
    component.app = mock_app  # type: ignore[assignment]

    frame = ttk.Frame(tk_root)
    component.calendar_frame = frame
    component.month_year_label = ttk.Label(tk_root)

    calendar.setfirstweekday(calendar.MONDAY)
    component._update_calendar()

    header_labels: dict[int, str] = {}
    date_buttons: list[tuple[int, int, int]] = []

    for child in frame.winfo_children():
        info = child.grid_info()
        row = int(info["row"])
        col = int(info["column"])
        if row == 0:
            header_labels[col] = child.cget("text")
        else:
            date_buttons.append((row, col, int(child.cget("text"))))

    # 月曜日始まりなのでヘッダーは 月, 火, 水, 木, 金, 土, 日
    assert [header_labels[c] for c in range(7)] == [
        "月",
        "火",
        "水",
        "木",
        "金",
        "土",
        "日",
    ]

    weekday_to_ja = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
    assert len(date_buttons) == 31
    for _r, col, day in date_buttons:
        dt = datetime(2026, 10, day)
        expected_label = weekday_to_ja[dt.weekday()]
        assert header_labels[col] == expected_label

    # 2026-10-18（日曜日）は column 6 に配置されていること
    oct_18_col = next(col for _r, col, day in date_buttons if day == 18)
    assert oct_18_col == 6
    assert header_labels[oct_18_col] == "日"

    frame.destroy()


def test_apply_locale_settings_sets_sunday_default(tk_root: tk.Tk) -> None:
    """_apply_locale_settings でデフォルトが sunday になることを検証する。"""
    import calendar
    from unittest.mock import MagicMock

    component = ScheduleHelperComponent.__new__(ScheduleHelperComponent)
    component.logger = logging.getLogger("test_schedule_helper")
    mock_app = MagicMock()
    mock_app.translator.return_value = "calendar_first_weekday"  # 未定義キー
    component.app = mock_app
    component._update_calendar = lambda: None  # type: ignore[method-assign]
    component._update_text_widget = lambda *args: None  # type: ignore[method-assign]

    component._apply_locale_settings()

    assert calendar.firstweekday() == calendar.SUNDAY


def test_calendar_with_real_translator_displays_japanese_weekdays_not_numbers(
    tk_root: tk.Tk,
) -> None:
    """本物の Translator を使用した際、ヘッダーが数字ではなく日本語の曜日になり、%a 書式化が正常に動作する（#186）。"""
    import calendar
    from tkinter import ttk
    from unittest.mock import MagicMock

    from src.utils.i18n import Translator

    sm = MagicMock()
    sm.get_setting.return_value = "ja"
    sm.event_dispatcher = MagicMock()
    translator = Translator(sm)

    component = ScheduleHelperComponent.__new__(ScheduleHelperComponent)
    component.logger = logging.getLogger("test_schedule_helper")
    component.today = datetime(2026, 10, 18, 12, 0)
    component.current_year = 2026
    component.current_month = 10
    component.selected_dates = [datetime(2026, 10, 18, 10, 0)]  # 日曜日

    mock_app = type("App", (), {})()
    mock_app.translator = translator
    component.app = mock_app  # type: ignore[assignment]

    frame = ttk.Frame(tk_root)
    component.calendar_frame = frame
    component.month_year_label = ttk.Label(tk_root)

    component.hour_var = tk.StringVar(master=tk_root, value="10")
    component.minute_var = tk.StringVar(master=tk_root, value="00")
    component.format_var = tk.StringVar(master=tk_root, value="%Y/%m/%d (%a) %H:%M")
    component.text_widget = tk.Text(tk_root)

    calendar.setfirstweekday(calendar.SUNDAY)
    component._update_calendar()

    # 1. 曜日ヘッダーが数字（0, 1, 2...）ではなく日本語（日, 月, 火...）であること
    header_texts = [
        child.cget("text")
        for child in frame.winfo_children()
        if int(child.grid_info()["row"]) == 0
    ]
    assert header_texts == ["日", "月", "火", "水", "木", "金", "土"]

    # 2. _update_text_widget で %a が "日" として出力されること（"weekdays_full"[weekday] の "w" などにならないこと）
    component._update_text_widget()
    generated_text = component.text_widget.get("1.0", "end-1c")
    assert "2026/10/18 (日) 10:00" in generated_text

    frame.destroy()
    component.text_widget.destroy()
