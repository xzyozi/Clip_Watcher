import csv
import io
from .base_plugin import Plugin

class TableFormatterPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.name = "Table Formatter"
        self.description = "Format CSV/TSV data as a table"
        self.version = "1.0.0"

    def detect_delimiter(self, text):
        """Detect if the text is CSV or TSV by counting delimiters"""
        comma_count = text.count(',')
        tab_count = text.count('\t')
        return '\t' if tab_count > comma_count else ','

    def format_data(self, text):
        """Format the data as a table"""
        try:
            delimiter = self.detect_delimiter(text)
            # Create a string buffer
            buffer = io.StringIO(text)
            # Read CSV/TSV data
            reader = csv.reader(buffer, delimiter=delimiter)
            rows = list(reader)
            
            if not rows:
                return text

            # Calculate column widths
            col_widths = []
            for col in range(len(rows[0])):
                width = max(len(str(row[col])) for row in rows if col < len(row))
                col_widths.append(width)

            # Format as table
            formatted_rows = []
            for row in rows:
                formatted_cells = []
                for i, cell in enumerate(row):
                    if i < len(col_widths):
                        formatted_cells.append(f"{cell:<{col_widths[i]}}")
                formatted_rows.append(" | ".join(formatted_cells))

            # Add header separator
            if len(formatted_rows) > 1:
                separator = "-" * len(formatted_rows[0])
                formatted_rows.insert(1, separator)

            return "\n".join(formatted_rows)

        except Exception as e:
            return f"Error formatting table: {str(e)}\n{text}"

    def process(self, text):
        """Process the clipboard text"""
        if not text.strip():
            return text
        
        # Check if text looks like CSV/TSV
        if ',' in text or '\t' in text:
            return self.format_data(text)
        return text