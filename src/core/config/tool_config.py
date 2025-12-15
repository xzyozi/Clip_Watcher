from src.gui.components import (
    ScheduleHelperComponent,
    HashCalculatorComponent,
    UnitConverterComponent,
)

TOOL_COMPONENTS = [
    {
        "name": "Calendar",
        "component": ScheduleHelperComponent,
        "setting_key": "show_calendar_tab"
    },
    {
        "name": "Hash Calculator",
        "component": HashCalculatorComponent,
        "setting_key": "show_hash_calculator_tab"
    },
    {
        "name": "Unit Converter",
        "component": UnitConverterComponent,
        "setting_key": "show_unit_converter_tab"
    }
]
