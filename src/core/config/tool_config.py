from src.gui.components.schedule_helper_component import ScheduleHelperComponent
from src.gui.components.hash_calculator_component import HashCalculatorComponent
from src.gui.components.unit_converter_component import UnitConverterComponent

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
