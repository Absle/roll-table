from pathlib import Path
from warnings import warn

from roll_table.errors import FieldResolveWarning, ResolveError
from roll_table.table import Table
from roll_table.utils import is_number, resolve_dice_arithmetic


class TableManager:
    tables: dict[str, Table]

    def __init__(self):
        self.tables = {}

    def _resolve_replacement_expression(
        self, depth, last_rolled_row: dict | None, op: str
    ) -> str:
        start = len(Table.OP_REPLACE_OPEN)
        end = op.find(Table.OP_FIELD_OPEN, start)
        if end < 0:
            end = len(op) - 1
        table_path = op[start:end]

        field = None
        if end != len(op) - 1:
            start = end + 1
            end = op.find(Table.OP_FIELD_CLOSE, start)
            if end < 0:
                warn(FieldResolveWarning("missing closing field bracket", depth, op))
            else:
                field = op[start:end]

        if table_path == Table.OP_PREV_ROW:
            if last_rolled_row is None:
                raise (
                    ResolveError(
                        f"'{Table.OP_PREV_ROW}' must not be first replacement",
                        depth,
                        op,
                    )
                )
        else:
            try:
                last_rolled_row = self.roll(table_path)
            except FileNotFoundError as e:
                extra = ResolveError(f"failed to open file", depth, op)
                e.add_note(f"{type(extra).__name__}: {str(extra)}")
                raise

        if field is not None:
            if field in last_rolled_row:
                value = last_rolled_row[field]
            else:
                warn(FieldResolveWarning("field not in table", depth, op))
                value = next(iter(last_rolled_row.values()))
        else:
            value = next(iter(last_rolled_row.values()))
        return str(value)

    def _resolve_dice_arithmetic_expression(self, op: str) -> str:
        start = len(Table.OP_REPLACE_OPEN)
        end = len(op) - 1
        expression = op[start:end]
        if is_number(expression):
            # Short-circuit out of the expression is already a number for some reason
            return expression
        else:
            return str(resolve_dice_arithmetic(expression))

    def add_table(self, path: str):
        table = Table(path)
        self.tables[str(table.path)] = table

    def get_table(self, path: str) -> Table:
        path_key = str(Path(path).absolute())
        if path_key not in self.tables:
            self.add_table(path)
        return self.tables[path_key]

    def resolve(self, rep_str: str, depth_limit: int = 100) -> str:
        for i in range(1, depth_limit + 1):
            if (
                Table.OP_REPLACE_OPEN not in rep_str
                or Table.OP_REPLACE_CLOSE not in rep_str
            ):
                break

            replace_ops: list[str] = []
            cursor = 0
            while cursor < len(rep_str):
                start = rep_str.find(Table.OP_REPLACE_OPEN, cursor)
                if start < 0:
                    # No more string replacements to be found
                    break
                cursor = start + len(Table.OP_REPLACE_OPEN)
                end = rep_str.find(Table.OP_REPLACE_CLOSE, cursor)
                cursor = end + len(Table.OP_REPLACE_CLOSE)
                replace_ops.append(rep_str[start : end + 1])

            row: dict | None = None
            replacements: list[str] = []
            for op in replace_ops:
                if op[len(Table.OP_REPLACE_OPEN)] not in "+-012345679(":
                    # The start of the op does not indicate dice or aritmetic
                    value = self._resolve_replacement_expression(i, row, op)
                else:
                    value = self._resolve_dice_arithmetic_expression(op)
                replacements.append(value)

            for op, replacement in zip(replace_ops, replacements):
                rep_str = rep_str.replace(op, replacement, 1)
        return rep_str

    def roll(self, table_path: str) -> dict:
        path_key = str(Path(table_path).absolute())
        if path_key not in self.tables:
            self.add_table(table_path)
        return self.tables[path_key].roll()
