from pathlib import Path

from roll_table.parsing.expression import ReplacementString
from roll_table.table import Table


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

    def resolve(self, rep_str: ReplacementString, depth_limit: int = 100) -> str:
        return rep_str._resolve(self, depth_limit)

    def roll(self, table_path: Path) -> dict:
        return self.get_table(table_path).roll()
