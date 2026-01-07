import ast
import random
import re
from pathlib import Path
from warnings import warn

from roll_table.errors import FieldResolveWarning, ResolveError, UnsafeExpressionError
from roll_table.table import Table

DICE_RE = re.compile(r"([0-9]+)d([0-9]+)")
MATH_CHARS = "0123456789()%*/+-"

LEGAL_OP_KINDS = [ast.BinOp, ast.UnaryOp, ast.Constant]
LEGAL_BINARY_OPS = [ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow]
LEGAL_UNARY_OPS = [ast.UAdd, ast.USub]
LEGAL_AST_NODES = LEGAL_OP_KINDS + LEGAL_BINARY_OPS + LEGAL_UNARY_OPS


def _roll_dice(num_dice: int, num_sides: int) -> int:
    if num_dice <= 0 or num_sides <= 0:
        return 0
    return sum([random.randint(1, num_sides) for _ in range(num_dice)])


def _resolve_dice_str(dice_str: str) -> int | float:
    expression = dice_str
    for num_dice, num_sides in DICE_RE.findall(dice_str):
        roll = _roll_dice(int(num_dice), int(num_sides))
        to_replace = num_dice + "d" + num_sides
        expression = expression.replace(to_replace, str(roll), 1)

    no_whitespace_expr = "".join(expression.split())
    if not all([c in MATH_CHARS for c in no_whitespace_expr]):
        raise UnsafeExpressionError(
            "found non-math character in expression", dice_str, expression
        )

    tree = ast.parse(expression, mode="eval")
    # print(ast.dump(tree, indent=2))

    # Walk through the AST and raise an exception if any illegal ops are found
    for i, node in enumerate(ast.walk(tree)):
        if type(node) is ast.Expression:
            if i == 0:
                # Only the first node in the tree can be an expression
                continue
            else:
                raise UnsafeExpressionError(
                    "found invalid Expression node", dice_str, expression
                )
        elif type(node) in LEGAL_AST_NODES:
            continue
        else:
            raise UnsafeExpressionError(
                f"found invalid node type {type(node).__name__}",
                dice_str,
                expression,
            )
    return eval(compile(tree, "<string>", "eval"), {"__builtins__": {}})


class TableManager:
    tables: dict[str, Table]

    def __init__(self):
        self.tables = {}

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
                        warn(
                            FieldResolveWarning("missing closing field bracket", i, op)
                        )
                    else:
                        field = op[start:end]

                if table_path == Table.OP_PREV_ROW:
                    if row is None:
                        raise (
                            ResolveError(
                                f"'{Table.OP_PREV_ROW}' must not be first replacement",
                                i,
                                op,
                            )
                        )
                else:
                    try:
                        row = self.roll(table_path)
                    except FileNotFoundError as e:
                        extra = ResolveError(f"failed to open file", i, op)
                        e.add_note(f"{type(extra).__name__}: {str(extra)}")
                        raise e

                if field is not None:
                    if field in row:
                        value = row[field]
                    else:
                        warn(FieldResolveWarning("field not in table", i, op))
                        value = next(iter(row.values()))
                else:
                    value = next(iter(row.values()))

                replacements.append(str(value))

            for op, replacement in zip(replace_ops, replacements):
                rep_str = rep_str.replace(op, replacement, 1)
        return rep_str

    def roll(self, table_path: str) -> dict:
        path_key = str(Path(table_path).absolute())
        if path_key not in self.tables:
            self.add_table(table_path)
        return self.tables[path_key].roll()


# TODO: remove
if __name__ == "__main__":
    # Should print -30.0
    print(_resolve_dice_str("-(1 + 2 - 3 * 4 / 5 ** 6 // 7) - +(8 + 9 + 10)"))

    histo = {}
    for _ in range(1000):
        result = _resolve_dice_str("2d6")
        if result in histo:
            histo[result] += 1
        else:
            histo[result] = 1
    for k in range(15):
        if k in histo:
            print(f"{k}: {histo[k]}")
