from __future__ import annotations

import calendar
import logging
import tkinter as tk
from datetime import datetime
from tkinter import Event, messagebox, ttk
from typing import TYPE_CHECKING, Any

from src.gui.base.base_frame_gui import BaseFrameGUI
from src.gui.custom_widgets import CustomText
from src.plugins.base_plugin import Plugin

if TYPE_CHECKING:
    from src.core.base_application import BaseApplication


class ScheduleHelperComponent(BaseFrameGUI):
    """
    A GUI component to help create texts related to dates and times.
    """
    def __init__(self, master: tk.Misc, app_instance: BaseApplication) -> None:
        super().__init__(master, app_instance)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ScheduleHelperComponent.")

        self.today = datetime.now()
        self.current_year = self.today.year
        self.current_month = self.today.month
        self.selected_dates: list[datetime] = []

        self.hour_var = tk.StringVar(value=f"{self.today.hour:02d}")
        self.minute_var = tk.StringVar(value="00")

        self.date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
            "%Y年%m月%d日(%a)",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
            "%Y年%m月%d日 %H:%M",
            "%Y年%m月%d日(%a) %H:%M",
            "%Y年%m月%d日(%a) %H:%M～",
        ]
        self.format_var = tk.StringVar(value=self.date_formats[7])

        self._create_widgets()

        # Subscribe to language changes and apply initial settings
        self.app.event_dispatcher.subscribe("LANGUAGE_CHANGED", self._apply_locale_settings) # type: ignore
        self._apply_locale_settings()

        # Unsubscribe when the widget is destroyed to prevent errors.
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event: Event) -> None:
        """Unsubscribes the listener when the widget is destroyed."""
        if event.widget == self:
            self.app.event_dispatcher.unsubscribe("LANGUAGE_CHANGED", self._apply_locale_settings) # type: ignore

    def _apply_locale_settings(self, *args: Any) -> None:
        """Applies locale-specific settings like the first day of the week and updates UI."""
        self.logger.info("Applying locale settings to calendar.")

        # Get the first day of the week from translation, with a fallback
        key = "calendar_first_weekday"
        first_day_str: str = self.app.translator(key) # type: ignore
        if first_day_str == key:  # Key not found, use default
            first_day_str = "monday"

        day_map = {
            "monday": calendar.MONDAY,
            "tuesday": calendar.TUESDAY,
            "wednesday": calendar.WEDNESDAY,
            "thursday": calendar.THURSDAY,
            "friday": calendar.FRIDAY,
            "saturday": calendar.SATURDAY,
            "sunday": calendar.SUNDAY
        }
        first_day = day_map.get(first_day_str.lower(), calendar.MONDAY)
        calendar.setfirstweekday(first_day)

        # Redraw the calendar and update the text widget to reflect changes
        self._update_calendar()
        self._update_text_widget()

    def _create_widgets(self) -> None:
        main_paned_window = tk.PanedWindow(self, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        main_paned_window.pack(fill=tk.BOTH, expand=True)

        controls_frame = ttk.Frame(main_paned_window, padding=5)
        main_paned_window.add(controls_frame, height=360)

        calendar_part_frame = ttk.Frame(controls_frame)
        calendar_part_frame.pack(fill=tk.X)

        nav_frame = ttk.Frame(calendar_part_frame)
        nav_frame.pack(pady=5)

        ttk.Button(nav_frame, text="<", command=self._prev_month, width=3).pack(side=tk.LEFT)
        self.month_year_label = ttk.Label(nav_frame, text="", width=18, anchor="center")
        self.month_year_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text=">", command=self._next_month, width=3).pack(side=tk.LEFT)
        ttk.Button(nav_frame, text="Today", command=self._go_to_today).pack(side=tk.LEFT, padx=10)

        self.calendar_frame = ttk.Frame(calendar_part_frame)
        self.calendar_frame.pack(pady=5)

        time_format_frame = ttk.Frame(controls_frame)
        time_format_frame.pack(fill=tk.X, pady=10)

        time_frame = ttk.LabelFrame(time_format_frame, text="Time")
        time_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        hour_values = [f"{h:02d}" for h in range(24)]
        minute_values = ["00", "15", "30", "45"]
        hour_combo = ttk.Combobox(time_frame, textvariable=self.hour_var, values=hour_values, width=4)
        hour_combo.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        minute_combo = ttk.Combobox(time_frame, textvariable=self.minute_var, values=minute_values, width=4)
        minute_combo.pack(side=tk.LEFT, padx=5, pady=5)

        format_frame = ttk.LabelFrame(time_format_frame, text="Format")
        format_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        format_combo = ttk.Combobox(format_frame, textvariable=self.format_var, values=self.date_formats, width=30)
        format_combo.pack(pady=5, padx=5)
        format_combo.bind("<<ComboboxSelected>>", self._update_text_widget)

        editor_frame = ttk.LabelFrame(main_paned_window, text="Generated Text")
        main_paned_window.add(editor_frame)

        button_bar_frame = ttk.Frame(editor_frame)
        button_bar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        ttk.Button(button_bar_frame, text="Copy to Clipboard", command=self._copy_to_clipboard).pack(side=tk.RIGHT)
        ttk.Button(button_bar_frame, text="Clear", command=self._clear_text).pack(side=tk.RIGHT, padx=5)

        self.text_scrollbar = ttk.Scrollbar(editor_frame, orient="vertical")
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_widget = CustomText(editor_frame, wrap=tk.WORD, relief=tk.FLAT, yscrollcommand=self.text_scrollbar.set, app=self.app)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text_scrollbar.config(command=self.text_widget.yview)

        self.logger.info("ScheduleHelperComponent widgets created.")

    def _update_calendar(self) -> None:
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()

        self.month_year_label.config(text=f"{self.current_year} / {self.current_month:02d}")

        days: list[str] = self.app.translator("days_short") # type: ignore
        for i, day in enumerate(days):
            ttk.Label(self.calendar_frame, text=day, width=5, anchor="center").grid(row=0, column=i, padx=2, pady=2)

        month_calendar = calendar.monthcalendar(self.current_year, self.current_month)
        for r, week in enumerate(month_calendar, 1):
            for c, day in enumerate(week): # type: ignore
                if day == 0:
                    continue

                btn = ttk.Button(self.calendar_frame, text=str(day), width=4, command=lambda d=day: self._select_date(d)) # type: ignore
                btn.grid(row=r, column=c, padx=1, pady=1)

                if self.current_year == self.today.year and self.current_month == self.today.month and day == self.today.day:
                    btn.configure(style="Today.TButton")

                is_selected = any(d.year == self.current_year and d.month == self.current_month and d.day == day for d in self.selected_dates)
                if is_selected:
                    btn.configure(style="Selected.TButton")

    def _go_to_today(self) -> None:
        self.current_year = self.today.year
        self.current_month = self.today.month
        self._update_calendar()
        self.logger.info("Calendar moved to today's month.")

    def _prev_month(self) -> None:
        self.current_month -= 1
        if self.current_month == 0:
            self.current_month = 12
            self.current_year -= 1
        self._update_calendar()

    def _next_month(self) -> None:
        self.current_month += 1
        if self.current_month == 13:
            self.current_month = 1
            self.current_year += 1
        self._update_calendar()

    def _select_date(self, day: int) -> None:
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
        except ValueError:
            hour, minute = self.today.hour, self.today.minute

        new_date_for_check = datetime(self.current_year, self.current_month, day)

        found_date: datetime | None = None
        for d in self.selected_dates:
            if d.year == new_date_for_check.year and d.month == new_date_for_check.month and d.day == new_date_for_check.day:
                found_date = d
                break

        if found_date:
            self.selected_dates.remove(found_date)
        else:
            new_date_with_time = new_date_for_check.replace(hour=hour, minute=minute)
            self.selected_dates.append(new_date_with_time)

        self.selected_dates.sort()
        self._update_calendar()
        self._update_text_widget()
        self.logger.info(f"Selected dates: {len(self.selected_dates)}")

    def _clear_text(self) -> None:
        self.selected_dates.clear()
        self.text_widget.delete(1.0, tk.END)
        self._update_calendar()
        self.logger.info("Cleared all selected dates and text.")

    def _copy_to_clipboard(self) -> None:
        content = self.text_widget.get("1.0", "end-1c")
        if not content:
            self.logger.info("Nothing to copy.")
            return
        try:
            self.master.clipboard_clear()
            self.master.clipboard_append(content)
            self.logger.info("Copied generated text to clipboard.")
            messagebox.showinfo("Copied", "テキストをクリップボードにコピーしました。", parent=self)
        except tk.TclError:
            self.logger.error("Failed to copy text to clipboard.")
            messagebox.showerror("Error", "クリップボードへのコピーに失敗しました。", parent=self)

    def _update_text_widget(self, event: Event | None = None) -> None:
        try:
            format_str = self.format_var.get()

            self.text_widget.delete(1.0, tk.END)

            output_lines = []
            for full_date in self.selected_dates:
                if "%a" in format_str:
                    weekdays: list[str] = self.app.translator("weekdays_full") # type: ignore
                    day_of_week = weekdays[full_date.weekday()]
                    temp_format = format_str.replace("%a", "__DAY_OF_WEEK__")
                    formatted_text = full_date.strftime(temp_format).replace("__DAY_OF_WEEK__", day_of_week)
                else:
                    formatted_text = full_date.strftime(format_str)
                output_lines.append(formatted_text)

            self.text_widget.insert(tk.END, "\n".join(output_lines))

        except (ValueError, TypeError) as e:
            self.logger.error(f"Error updating text widget: {e}")

class ScheduleHelperPlugin(Plugin):
    """
    Plugin wrapper for the Schedule Helper GUI tool.
    """
    @property
    def name(self) -> str:
        return "Calendar"

    @property
    def description(self) -> str:
        return "A GUI tool to help create texts related to dates and times."

    def has_gui_component(self) -> bool:
        return True

    def create_gui_component(self, parent: ttk.Notebook, app_instance: BaseApplication) -> ttk.Frame | None:
        return ScheduleHelperComponent(parent, app_instance) # type: ignore
