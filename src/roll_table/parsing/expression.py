import ast
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from roll_table.parsing import _consume
from roll_table.utils import DICE_RE, roll_dice

if TYPE_CHECKING:
    # Have to do this to avoid circular import during an actual run
    from roll_table.table_manager import TableManager

ARITH_CHARS = "0123456789()%*/+-"
ARITH_STARTERS = "+-0123456789("

LEGAL_OP_KINDS = [ast.BinOp, ast.UnaryOp, ast.Constant]
LEGAL_BINARY_OPS = [ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow]
LEGAL_UNARY_OPS = [ast.UAdd, ast.USub]
LEGAL_AST_NODES = LEGAL_OP_KINDS + LEGAL_BINARY_OPS + LEGAL_UNARY_OPS


class ExpressionParseError(Exception):
    def __init__(self, expr: str, message: str):
        super().__init__(
            f"{Syntax.REPLACE_OPEN.value}{expr}{Syntax.REPLACE_CLOSE.value}: {message}"
        )


class Syntax(StrEnum):
    FIELD_OPEN = "["
    FIELD_CLOSE = "]"
    PREV_REF = "~"
    REPLACE_OPEN = "${"
    REPLACE_CLOSE = "}"


class Expression:
    _raw_expr: str
    _resolved_expr: "str | ReplacementString | None"

    def __init__(self, raw_expr: str):
        self._raw_expr = raw_expr
        self._resolved_expr = None

    def __repr__(self) -> str:
        typename = type(self).__name__
        open = Syntax.REPLACE_OPEN.value
        close = Syntax.REPLACE_CLOSE.value
        return f"{typename}({open}{self._raw_expr}{close})"

    def __str__(self) -> str:
        if self._resolved_expr is not None:
            return str(self._resolved_expr)
        else:
            open = Syntax.REPLACE_OPEN.value
            close = Syntax.REPLACE_CLOSE.value
            return f"{open}{self._raw_expr}{close}"

    @property
    def is_resolved(self) -> bool:
        return self._resolved_expr is not None

    @property
    def raw_expr(self):
        return Syntax.REPLACE_OPEN.value + self._raw_expr + Syntax.REPLACE_CLOSE.value

    @property
    def resolved_expr(self) -> "str | ReplacementString | None":
        return self._resolved_expr

    @staticmethod
    def _parse(raw_expr: str, namespace: dict[str, Path]) -> "Expression | str":
        if len(raw_expr) == 0:
            # TODO: log warning about empty expression
            return Syntax.REPLACE_OPEN.value + raw_expr + Syntax.REPLACE_CLOSE.value

        try:
            if raw_expr[0] in ARITH_STARTERS:
                return DiceArithExpr(raw_expr)
            else:
                return RefExpr(raw_expr, namespace)
        except:
            # TODO: log warning based on caught exception
            return Syntax.REPLACE_OPEN.value + raw_expr + Syntax.REPLACE_CLOSE.value


class DiceArithExpr(Expression):
    def __init__(self, raw_expr: str):
        safe, reason = DiceArithExpr._is_safe_and_valid(raw_expr)
        if not safe:
            raise ExpressionParseError(raw_expr, reason)
        super().__init__(raw_expr)

    @staticmethod
    def _is_safe_and_valid(raw_expr: str) -> tuple[bool, str]:
        # Dice rolls are safe, so just resolve them to get to the arithmetic
        pure_arithmetic = DiceArithExpr._resolve_dice_rolls(raw_expr)

        # An expression just being a single dice roll is a common case
        # Try to return early and skip making an AST if we can
        try:
            _ = int(pure_arithmetic)
            return True, ""
        except:
            pass

        no_ws = "".join(pure_arithmetic.split())
        if any([c not in ARITH_CHARS for c in no_ws]):
            return False, "found non-arithmetic character in expression"

        tree = ast.parse(pure_arithmetic, mode="eval")
        for i, node in enumerate(ast.walk(tree)):
            if type(node) is ast.Expression:
                if i == 0 and type(node.body) in LEGAL_AST_NODES:
                    # Only an expression that is the first node in the tree and contains a
                    # legal AST node in its body is allowed
                    continue
                else:
                    reason = (
                        f"at tree index {i}: found invalid Expression node; body type = "
                        f"{type(node.body).__name__}"
                    )
                    return False, reason
            elif type(node) in LEGAL_AST_NODES:
                continue
            else:
                reason = (
                    f"at tree index {i}: found invalid node type: {type(node).__name__}"
                )
                return False, reason

        pseudofile = f"<{Syntax.FIELD_OPEN.value}{raw_expr}{Syntax.FIELD_CLOSE.value}>"
        value = eval(compile(tree, pseudofile, "eval"), {"__builtins__": {}})
        if type(value) is not float and type(value) is not int:
            typename = type(value).__name__
            return False, f"test evaluation returned invalid value: {typename}({value})"
        return True, ""

    @staticmethod
    def _resolve_dice_rolls(raw_expr: str) -> str:
        pure_arithmetic = raw_expr
        for num_dice, num_sides in DICE_RE.findall(pure_arithmetic):
            roll = roll_dice(int(num_dice), int(num_sides))
            to_replace = num_dice + "d" + num_sides
            pure_arithmetic = pure_arithmetic.replace(to_replace, str(roll), 1)
        return pure_arithmetic

    def _resolve(self) -> str:
        pure_arithmetic = DiceArithExpr._resolve_dice_rolls(self._raw_expr)
        tree = ast.parse(pure_arithmetic, mode="eval")
        pseudofile = f"<{repr(self)}>"

        # We can safely use eval directly here because we verified the expression is only
        # dice rolls and arithmetic during __init__
        self._resolved_expr = str(
            eval(compile(tree, pseudofile, "eval"), {"__builtins__": {}})
        )
        return self._resolved_expr


class RefExpr(Expression):
    _alias: str
    _path: Path | None
    _field_name: str | None

    def __init__(self, raw_expr: str, namespace: dict[str, Path]):
        super().__init__(raw_expr)

        alias, separator, raw_expr = _consume(raw_expr, [Syntax.FIELD_OPEN])
        alias.strip()
        raw_expr.strip()
        if len(alias) == 0:
            raise ExpressionParseError(raw_expr, "empty aliases are not allowed")
        elif alias not in namespace and alias != Syntax.PREV_REF.value:
            raise ExpressionParseError(raw_expr, f"could not resolve alias '{alias}'")

        self._alias = alias
        if alias == Syntax.PREV_REF.value:
            self._path = None
        else:
            self._path = namespace[alias]
            if not self._path.is_file():
                msg = (
                    f"alias '{alias}' resolved to path '{self._path}', but that path is "
                    "not a valid file"
                )
                raise ExpressionParseError(raw_expr, msg)

        if separator is None:
            self._field_name = None
        else:
            field_name, separator, raw_expr = _consume(raw_expr, [Syntax.FIELD_CLOSE])
            field_name.strip()
            if separator is None:
                msg = f"unclosed field, expected '{Syntax.FIELD_CLOSE}'"
                raise ExpressionParseError(raw_expr, msg)
            else:
                self._field_name = field_name

    def _resolve(
        self, table_manager: "TableManager", prev_roll: dict | None
    ) -> tuple["ReplacementString | str", dict | None]:
        if self._alias == Syntax.PREV_REF.value:
            if prev_roll is None:
                # TODO: issue warning about first ref expr being a prev ref
                return self.raw_expr, None
            row = prev_roll
        else:
            # self._path is only None if _alias is a PREV_REF
            row = table_manager.roll(self._path)  # type: ignore

        if self._field_name is not None:
            if self._field_name in row:
                value = row[self._field_name]
            else:
                # TODO: log warning about invalid field name
                value = next(iter(row.values()))
        else:
            value = next(iter(row.values()))

        if type(value) is not ReplacementString:
            value = str(value)

        return value, row


class ReplacementString:
    _original_elements: list[str | Expression]
    _resolved_elements: list[str | Expression] | None

    def __init__(self, elements: list[str | Expression]):
        self._original_elements = elements
        self._resolved_elements = None

    @staticmethod
    def _parse(raw_str: str, namespace: dict[str, Path]) -> "ReplacementString | str":
        orig_str = raw_str
        elements = []
        while len(raw_str) > 0:
            non_expr, separator, raw_str = _consume(raw_str, [Syntax.REPLACE_OPEN])
            if len(non_expr) > 0:
                elements.append(non_expr)

            if separator is None:
                # Reached the end of raw_str with no more expression, break early
                break

            raw_expr, separator, raw_str = _consume(raw_str, [Syntax.REPLACE_CLOSE])
            if separator is None:
                # Reached end of raw_str without closing the expression
                # Treat it as a plain string and break early
                # TODO: log warning about skipping an incomplete expression here
                elements.append(raw_expr)
                break
            raw_expr = raw_expr.strip()

            expression = Expression._parse(raw_expr, namespace)
            elements.append(expression)

        if len(elements) > 0 and any(
            [issubclass(type(elem), Expression) for elem in elements]
        ):
            return ReplacementString(elements)
        else:
            return orig_str

    def _resolve(self, table_manager: "TableManager", depth_limit: int) -> str:
        current_elements = self._original_elements
        prev_roll: dict | None = None
        for _ in range(1, depth_limit + 1):
            if not any([type(e) is not str for e in current_elements]):
                # out of non-string elements, break early
                break

            next_elements: list[str | Expression] = []
            for elem in current_elements:
                if type(elem) is str:
                    next_elements.append(elem)
                elif type(elem) is DiceArithExpr:
                    next_elements.append(elem._resolve())

                elif type(elem) is RefExpr:
                    resolved, prev_roll = elem._resolve(table_manager, prev_roll)

                    if type(resolved) is ReplacementString:
                        next_elements += [
                            sub_elem for sub_elem in resolved._original_elements
                        ]
                    elif type(resolved) is str:
                        next_elements.append(resolved)
                else:
                    # Should be unreachable
                    # TODO: issue warning about unimplemented reference type
                    next_elements.append(elem.raw_expr)  # type: ignore
            current_elements = next_elements
        self._resolved_elements = current_elements
        return "".join([str(e) for e in current_elements])


def parse_replacement_string(
    raw_str: str, namespace: dict[str, Path]
) -> ReplacementString | str:
    return ReplacementString._parse(raw_str, namespace)
