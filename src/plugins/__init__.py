"""
This package dynamically loads all converter plugins from the current directory.
"""
from .base64_converter_plugin import Base64ConverterPlugin
from .base_plugin import Plugin
from .csv_formatter_plugin import CSVFormatterPlugin
from .duplicate_line_remover_plugin import DuplicateLineRemoverPlugin
from .general_case_converter_plugin import GeneralCaseConverterPlugin
from .html_escape_plugin import HTMLEscapePlugin
from .json_formatter_plugin import JSONFormatterPlugin
from .line_sorter_plugin import LineSorterPlugin
from .table_formatter_plugin import TableFormatterPlugin
from .uppercase_converter_plugin import UppercaseConverterPlugin
from .url_converter_plugin import URLConverterPlugin
from .whitespace_normalizer_plugin import WhitespaceNormalizerPlugin

# List of all plugin classes to be dynamically loaded by the PluginManager.
# The PluginManager will instantiate these classes.
# This approach allows for easy extension by simply adding a new plugin file
# and updating this list.
__all__ = [
    "Plugin",
    "Base64ConverterPlugin",
    "CSVFormatterPlugin",
    "DuplicateLineRemoverPlugin",
    "GeneralCaseConverterPlugin",
    "HTMLEscapePlugin",
    "JSONFormatterPlugin",
    "LineSorterPlugin",
    "TableFormatterPlugin",
    "UppercaseConverterPlugin",
    "URLConverterPlugin",
    "WhitespaceNormalizerPlugin",
]
