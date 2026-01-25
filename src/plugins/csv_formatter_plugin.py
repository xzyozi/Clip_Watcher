import csv
import io

from .base_plugin import Plugin


class CSVFormatterPlugin(Plugin):
    @property
    def name(self) -> str:
        return "CSV/TSV Formatter"

    @property
    def description(self) -> str:
        return "Formats CSV or TSV data into aligned columns."

    def process(self, text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            return text

        # Try to detect delimiter (comma or tab)
        delimiter = ','
        if '\t' in text and ',' not in text:
            delimiter = '\t'
        elif '\t' in text and ',' in text:
            # If both are present, count occurrences to guess
            if text.count('\t') > text.count(','):
                delimiter = '\t'
            else:
                delimiter = ','

        # Use StringIO to treat string as a file
        f = io.StringIO(text)
        reader = csv.reader(f, delimiter=delimiter)

        rows = []
        try:
            for row in reader:
                rows.append(row)
        except csv.Error:
            # Not a valid CSV/TSV, return original text
            return text

        if not rows:
            return text

        # Calculate max width for each column
        num_columns = max(len(row) for row in rows)
        column_widths = [0] * num_columns
        for row in rows:
            for i, cell in enumerate(row):
                if i < num_columns:
                    column_widths[i] = max(column_widths[i], len(cell))

        formatted_lines = []
        for row in rows:
            formatted_row_parts = []
            for i, cell in enumerate(row):
                if i < num_columns:
                    formatted_row_parts.append(cell.ljust(column_widths[i]))
            formatted_lines.append(delimiter.join(formatted_row_parts))

        return '\n'.join(formatted_lines)
