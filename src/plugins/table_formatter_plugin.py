import csv
import io

from .base_plugin import Plugin


class TableFormatterPlugin(Plugin):

    @property
    def name(self) -> str:
        return "Table Formatter"

    @property
    def description(self) -> str:
        return "Formats comma-separated or tab-separated text into a simple table."

    def process(self, text: str) -> str:
        if not text.strip():
            return text

        # Detect delimiter
        if '\t' in text and ',' not in text:
            delimiter = '\t'
        elif ',' in text:
            delimiter = ','
        else:
            return text

        try:
            # Read the data
            string_io = io.StringIO(text)
            reader = csv.reader(string_io, delimiter=delimiter)
            rows = list(reader)

            if not rows:
                return text

            # Calculate max width for each column
            num_columns = max(len(row) for row in rows)
            col_widths = [0] * num_columns
            for row in rows:
                for i, cell in enumerate(row):
                    col_widths[i] = max(col_widths[i], len(cell.strip()))

            # Format table
            formatted_table = []
            for row in rows:
                formatted_row = []
                for i, cell in enumerate(row):
                    formatted_row.append(cell.strip().ljust(col_widths[i]))
                # Ensure row has num_columns items
                while len(formatted_row) < num_columns:
                    formatted_row.append(''.ljust(col_widths[len(formatted_row)]))
                formatted_table.append(' | '.join(formatted_row))

            return '\n'.join(formatted_table)
        except Exception:
            return text # Return original text if formatting fails
