"""ScheduleHelperComponent / ScheduleHelperPlugin の実 Tk 単体テスト。"""

from __future__ import annotations

import calendar
import tkinter as tk
from collections.abc import Generator
from datetime import datetime
from tkinter import ttk
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.plugins.implementations.schedule_helper_plugin import (
    ScheduleHelperComponent,
    ScheduleHelperPlugin,
)

WEEKDAYS_FULL = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
DAYS_SHORT = ["日", "月", "火", "水", "木", "金", "土"]


def _make_translator(first_weekday: str | None = "monday") -> Any:
    table: dict[str, Any] = {
        "days_short": DAYS_SHORT,
        "weekdays_full": WEEKDAYS_FULL,
    }
    if first_weekday is not None:
        table["calendar_first_weekday"] = first_weekday
    return lambda key: table.get(key, key)


@pytest.fixture
def restore_first_weekday() -> Generator[None, None, None]:
    """calendar.setfirstweekday はプロセス全体に影響するため、テスト後に戻す。"""
    original = calendar.firstweekday()
    yield
    calendar.setfirstweekday(original)


def _fake_master(
    monkeypatch: pytest.MonkeyPatch, component: ScheduleHelperComponent
) -> MagicMock:
    """クリップボード操作だけを差し替える。

    master は Tk のウィジェット階層（destroy 等）でも使われるため、テスト終了時に
    monkeypatch が元へ戻す（component フィクスチャの後始末より先に実行される）。
    """
    fake = MagicMock()
    monkeypatch.setattr(component, "master", fake)
    return fake


def _make_app(first_weekday: str | None = "monday") -> MagicMock:
    app = MagicMock()
    app.translator = _make_translator(first_weekday)
    return app


@pytest.fixture
def component(
    tk_root: tk.Tk, restore_first_weekday: None
) -> Generator[ScheduleHelperComponent, None, None]:
    comp = ScheduleHelperComponent(tk_root, _make_app())
    comp.pack()
    yield comp
    comp.destroy()


def test_init_applies_first_weekday_and_renders_calendar(
    component: ScheduleHelperComponent,
) -> None:
    assert calendar.firstweekday() == calendar.MONDAY
    assert component.month_year_label.cget("text") == (
        f"{component.current_year} / {component.current_month:02d}"
    )
    # 曜日見出し7個 + 当月の日付ボタン
    children = component.calendar_frame.winfo_children()
    labels = [c for c in children if isinstance(c, ttk.Label)]
    buttons = [c for c in children if isinstance(c, ttk.Button)]
    assert len(labels) == 7
    assert labels[0].cget("text") == "月"
    days_in_month = calendar.monthrange(
        component.current_year, component.current_month
    )[1]
    assert len(buttons) == days_in_month


def test_missing_first_weekday_translation_falls_back_to_sunday(
    tk_root: tk.Tk, restore_first_weekday: None
) -> None:
    comp = ScheduleHelperComponent(tk_root, _make_app(first_weekday=None))
    try:
        assert calendar.firstweekday() == calendar.SUNDAY
    finally:
        comp.destroy()


def test_unknown_first_weekday_value_falls_back_to_sunday(
    tk_root: tk.Tk, restore_first_weekday: None
) -> None:
    comp = ScheduleHelperComponent(tk_root, _make_app(first_weekday="someday"))
    try:
        assert calendar.firstweekday() == calendar.SUNDAY
    finally:
        comp.destroy()


def test_day_labels_use_index_when_translation_is_not_a_list(
    tk_root: tk.Tk, restore_first_weekday: None
) -> None:
    app = MagicMock()
    app.translator = lambda key: key  # days_short が文字列で返る場合
    comp = ScheduleHelperComponent(tk_root, app)
    try:
        labels = [
            c for c in comp.calendar_frame.winfo_children() if isinstance(c, ttk.Label)
        ]
        assert [lb.cget("text") for lb in labels] == [str(i) for i in range(7)]
    finally:
        comp.destroy()


def test_month_navigation_wraps_across_years(
    component: ScheduleHelperComponent,
) -> None:
    component.current_year, component.current_month = 2026, 1
    component._prev_month()
    assert (component.current_year, component.current_month) == (2025, 12)

    component._next_month()
    assert (component.current_year, component.current_month) == (2026, 1)

    component.current_month = 12
    component._next_month()
    assert (component.current_year, component.current_month) == (2027, 1)


def test_prev_and_next_month_within_year(component: ScheduleHelperComponent) -> None:
    component.current_year, component.current_month = 2026, 5
    component._prev_month()
    assert component.current_month == 4
    component._next_month()
    component._next_month()
    assert component.current_month == 6


def test_go_to_today_returns_to_current_month(
    component: ScheduleHelperComponent,
) -> None:
    component.current_year, component.current_month = 1999, 3
    component._go_to_today()
    assert component.current_year == component.today.year
    assert component.current_month == component.today.month


def test_select_date_adds_sorts_and_toggles_off(
    component: ScheduleHelperComponent,
) -> None:
    component.current_year, component.current_month = 2026, 3
    component.hour_var.set("09")
    component.minute_var.set("15")

    component._select_date(20)
    component._select_date(5)
    assert [d.day for d in component.selected_dates] == [5, 20]
    assert component.selected_dates[0] == datetime(2026, 3, 5, 9, 15)

    # 選択済みの日をもう一度選ぶと解除される
    component._select_date(5)
    assert [d.day for d in component.selected_dates] == [20]


def test_select_date_with_non_numeric_time_uses_today_time(
    component: ScheduleHelperComponent,
) -> None:
    component.today = datetime(2026, 1, 1, 7, 45)
    component.current_year, component.current_month = 2026, 1
    component.hour_var.set("xx")
    component._select_date(10)
    selected = component.selected_dates[0]
    assert (selected.hour, selected.minute) == (7, 45)


def test_calendar_marks_selected_day_with_selected_style(
    component: ScheduleHelperComponent,
) -> None:
    component.current_year, component.current_month = 2026, 3
    component._select_date(10)
    styled = [
        b
        for b in component.calendar_frame.winfo_children()
        if isinstance(b, ttk.Button) and str(b.cget("style")) == "Selected.TButton"
    ]
    assert [b.cget("text") for b in styled] == ["10"]


def test_calendar_marks_today_with_today_style(
    component: ScheduleHelperComponent,
) -> None:
    component._go_to_today()
    todays = [
        b
        for b in component.calendar_frame.winfo_children()
        if isinstance(b, ttk.Button) and str(b.cget("style")) == "Today.TButton"
    ]
    assert [b.cget("text") for b in todays] == [str(component.today.day)]


def test_text_widget_uses_selected_format(component: ScheduleHelperComponent) -> None:
    component.current_year, component.current_month = 2026, 3
    component.hour_var.set("10")
    component.minute_var.set("30")
    component.format_var.set("%Y-%m-%d %H:%M")
    component._select_date(2)
    component._select_date(1)
    assert component.text_widget.get("1.0", "end-1c") == (
        "2026-03-01 10:30\n2026-03-02 10:30"
    )


def test_text_widget_replaces_weekday_placeholder(
    component: ScheduleHelperComponent,
) -> None:
    component.current_year, component.current_month = 2026, 3
    component.format_var.set("%Y年%m月%d日(%a)")
    component._select_date(2)  # 2026-03-02 は月曜日
    assert component.text_widget.get("1.0", "end-1c") == "2026年03月02日(月曜日)"


def test_update_text_widget_logs_error_instead_of_raising(
    component: ScheduleHelperComponent,
) -> None:
    component.selected_dates = [datetime(2026, 3, 1)]
    with (
        patch.object(component.text_widget, "insert", side_effect=TypeError("bad")),
        patch.object(component.logger, "error") as log_error,
    ):
        component._update_text_widget()
    log_error.assert_called_once()


def test_clear_text_removes_selection_and_text(
    component: ScheduleHelperComponent,
) -> None:
    component.current_year, component.current_month = 2026, 3
    component._select_date(2)
    component._clear_text()
    assert component.selected_dates == []
    assert component.text_widget.get("1.0", "end-1c") == ""


def test_copy_to_clipboard_with_empty_text_does_nothing(
    component: ScheduleHelperComponent, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_master = _fake_master(monkeypatch, component)
    with patch("src.plugins.implementations.schedule_helper_plugin.messagebox") as box:
        component._copy_to_clipboard()
    fake_master.clipboard_clear.assert_not_called()
    box.showinfo.assert_not_called()


def test_copy_to_clipboard_copies_generated_text(
    component: ScheduleHelperComponent, monkeypatch: pytest.MonkeyPatch
) -> None:
    component.current_year, component.current_month = 2026, 3
    component.format_var.set("%Y-%m-%d")
    component._select_date(2)
    fake_master = _fake_master(monkeypatch, component)
    with patch("src.plugins.implementations.schedule_helper_plugin.messagebox") as box:
        component._copy_to_clipboard()
    fake_master.clipboard_clear.assert_called_once()
    fake_master.clipboard_append.assert_called_once_with("2026-03-02")
    box.showinfo.assert_called_once()


def test_copy_to_clipboard_reports_tcl_error(
    component: ScheduleHelperComponent, monkeypatch: pytest.MonkeyPatch
) -> None:
    component.current_year, component.current_month = 2026, 3
    component._select_date(2)
    fake_master = _fake_master(monkeypatch, component)
    fake_master.clipboard_clear.side_effect = tk.TclError("no clipboard")
    with patch("src.plugins.implementations.schedule_helper_plugin.messagebox") as box:
        component._copy_to_clipboard()
    box.showerror.assert_called_once()
    box.showinfo.assert_not_called()


def test_destroy_unsubscribes_from_language_changes(
    tk_root: tk.Tk, restore_first_weekday: None
) -> None:
    app = _make_app()
    comp = ScheduleHelperComponent(tk_root, app)
    handler = comp._apply_locale_settings
    comp.destroy()
    # 子ウィジェット（CustomText）の購読解除も含まれるため、本体の解除を探して確認する
    app.event_dispatcher.unsubscribe.assert_any_call("LANGUAGE_CHANGED", handler)


def test_plugin_metadata_and_gui_component(
    tk_root: tk.Tk, restore_first_weekday: None
) -> None:
    plugin = ScheduleHelperPlugin()
    assert plugin.name == "Calendar"
    assert plugin.description
    assert plugin.has_gui_component() is True

    notebook = ttk.Notebook(tk_root)
    comp = plugin.create_gui_component(notebook, _make_app())
    try:
        assert isinstance(comp, ScheduleHelperComponent)
    finally:
        if comp is not None:
            comp.destroy()
        notebook.destroy()
