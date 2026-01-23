from pathlib import Path

from roll_table.parsing.expression import ReplacementString
from roll_table.table import Table


DEFAULT_DEPTH = 100


class TableManager:
    tables: dict[str, Table]

    def __init__(self):
        self.tables = {}

    def add_table(self, path: Path):
        table = Table(path)
        path_key = str(table.path)
        self.tables[path_key] = table

    def get_table(self, path: Path) -> Table:
        path_key = str(path.absolute())
        if path_key not in self.tables:
            self.add_table(path)
        return self.tables[path_key]

    def resolve(
        self, rep_str: ReplacementString, depth_limit: int = DEFAULT_DEPTH
    ) -> str:
        return rep_str._resolve(self, depth_limit)

    def roll(self, table_path: Path) -> dict[str, str | ReplacementString]:
        return self.get_table(table_path).roll()

    def roll_resolve(
        self, table_path: Path, depth_limit: int = DEFAULT_DEPTH
    ) -> dict[str, str]:
        row = self.roll(table_path)
        for field_name in row.keys():
            value = row[field_name]
            if type(value) is ReplacementString:
                row[field_name] = self.resolve(value, depth_limit)
        # We know row will only have str values in it because we just resolved all the
        # ReplacementStrings in there
        return row  # type: ignore
