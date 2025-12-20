import tkinter as tk
from tkinter import ttk
import logging
from datetime import datetime

from src.gui.components.base_tool_component import BaseToolComponent

class UnitConverterComponent(BaseToolComponent):
    """
    A GUI component for converting units, including time.
    """
    @property
    def tool_name(self) -> str:
        return "Unit Converter"

    @property
    def setting_key(self) -> str:
        return "show_unit_converter_tab"

    def __init__(self, master, app_instance):
        super().__init__(master, app_instance)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing UnitConverterComponent.")

        self.conversions = {
            "Length": {
                "Meter": 1,
                "Centimeter": 0.01,
                "Inch": 0.0254,
                "Foot": 0.3048,
                "Yard": 0.9144,
                "Kilometer": 1000,
                "Mile": 1609.34
            },
            "Weight": {
                "Kilogram": 1,
                "Gram": 0.001,
                "Pound (lbs)": 0.453592,
                "Ounce": 0.0283495
            },
            "Temperature": {
                "Celsius": "celsius",
                "Fahrenheit": "fahrenheit",
                "Kelvin": "kelvin"
            },
            "Time": {
                "Unix Timestamp": "unix",
                "Datetime String": "datetime"
            }
        }

        self.category_var = tk.StringVar(value="Length")
        self.from_unit_var = tk.StringVar()
        self.to_unit_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar(value="Result:")

        self._create_widgets()
        self._on_category_change()

    def _create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Category selection
        category_frame = ttk.LabelFrame(main_frame, text="Category")
        category_frame.pack(fill=tk.X, padx=5, pady=5)
        category_combo = ttk.Combobox(category_frame, textvariable=self.category_var, values=list(self.conversions.keys()))
        category_combo.pack(fill=tk.X, padx=5, pady=5)
        category_combo.bind("<<ComboboxSelected>>", self._on_category_change)

        # Conversion frame
        conversion_frame = ttk.Frame(main_frame)
        conversion_frame.pack(fill=tk.X, padx=5, pady=5)

        # From
        from_frame = ttk.LabelFrame(conversion_frame, text="From")
        from_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.from_unit_combo = ttk.Combobox(from_frame, textvariable=self.from_unit_var)
        self.from_unit_combo.pack(fill=tk.X, padx=5, pady=5)
        self.from_unit_combo.bind("<<ComboboxSelected>>", self._convert)
        
        input_entry = ttk.Entry(from_frame, textvariable=self.input_var)
        input_entry.pack(fill=tk.X, padx=5, pady=5)
        input_entry.bind("<KeyRelease>", self._convert)

        # To
        to_frame = ttk.LabelFrame(conversion_frame, text="To")
        to_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.to_unit_combo = ttk.Combobox(to_frame, textvariable=self.to_unit_var)
        self.to_unit_combo.pack(fill=tk.X, padx=5, pady=5)
        self.to_unit_combo.bind("<<ComboboxSelected>>", self._convert)
        
        output_label = ttk.Label(to_frame, textvariable=self.output_var, anchor="w")
        output_label.pack(fill=tk.X, padx=5, pady=5)

    def _on_category_change(self, event=None):
        category = self.category_var.get()
        units = list(self.conversions[category].keys())
        self.from_unit_combo['values'] = units
        self.to_unit_combo['values'] = units
        if units:
            self.from_unit_var.set(units[0])
            self.to_unit_var.set(units[1] if len(units) > 1 else units[0])
        self._convert()

    def _convert(self, event=None):
        category = self.category_var.get()
        from_unit = self.from_unit_var.get()
        to_unit = self.to_unit_var.get()
        input_str = self.input_var.get()

        if not from_unit or not to_unit or not input_str:
            self.output_var.set("Result:")
            return

        if category == "Time":
            self._convert_time(input_str, from_unit, to_unit)
            return

        try:
            value = float(input_str)
        except ValueError:
            self.output_var.set("Result: Invalid number")
            return

        if category == "Temperature":
            result = self._convert_temperature(value, from_unit, to_unit)
            self.output_var.set(f"Result: {result:.4f}")
        else: # Length and Weight
            base_value = value * self.conversions[category][from_unit]
            result = base_value / self.conversions[category][to_unit]
            self.output_var.set(f"Result: {result:.4f}")

    def _convert_temperature(self, value, from_unit, to_unit):
        if from_unit == to_unit:
            return value
        # Convert to Celsius first
        if from_unit == "Fahrenheit":
            celsius = (value - 32) * 5/9
        elif from_unit == "Kelvin":
            celsius = value - 273.15
        else: # from_unit is Celsius
            celsius = value
        # Convert from Celsius to target unit
        if to_unit == "Fahrenheit":
            return (celsius * 9/5) + 32
        elif to_unit == "Kelvin":
            return celsius + 273.15
        else: # to_unit is Celsius
            return celsius

    def _convert_time(self, input_str, from_unit, to_unit):
        if from_unit == to_unit:
            self.output_var.set(f"Result: {input_str}")
            return

        try:
            if from_unit == "Unix Timestamp":
                # From Timestamp to Datetime
                ts = float(input_str)
                dt_obj = datetime.fromtimestamp(ts)
                result = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                self.output_var.set(f"Result: {result}")
            elif from_unit == "Datetime String":
                # From Datetime to Timestamp
                # Try a few common formats
                dt_obj = None
                formats_to_try = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%Y-%m-%d',
                    '%Y/%m/%d %H:%M:%S',
                    '%Y/%m/%d %H:%M',
                    '%Y/%m/%d',
                ]
                for fmt in formats_to_try:
                    try:
                        dt_obj = datetime.strptime(input_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if dt_obj is None:
                    raise ValueError("Invalid datetime format")

                result = dt_obj.timestamp()
                self.output_var.set(f"Result: {result}")
        except (ValueError, TypeError) as e:
            self.output_var.set(f"Result: Error")
            self.logger.error(f"Time conversion error: {e}")