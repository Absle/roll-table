import ast
import random
import re
from typing import Any

from roll_table.errors import UnsafeExpressionError

DICE_RE = re.compile(r"([0-9]+)d([0-9]+)")
ARITHMETIC_CHARS = "0123456789()%*/+-"

LEGAL_OP_KINDS = [ast.BinOp, ast.UnaryOp, ast.Constant]
LEGAL_BINARY_OPS = [ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow]
LEGAL_UNARY_OPS = [ast.UAdd, ast.USub]
LEGAL_AST_NODES = LEGAL_OP_KINDS + LEGAL_BINARY_OPS + LEGAL_UNARY_OPS


def dice_range(num_dice: int, num_sides: int) -> range:
    if num_dice <= 0 or num_sides <= 0:
        return range(0)
    return range(num_dice, num_dice * num_sides + 1)


def roll_dice(num_dice: int, num_sides: int) -> int:
    if num_dice <= 0 or num_sides <= 0:
        return 0
    return sum([random.randint(1, num_sides) for _ in range(num_dice)])


def _safe_arithmetic_eval(expression: str) -> int | float:
    no_whitespace_expr = "".join(expression.split())
    if not all([c in ARITHMETIC_CHARS for c in no_whitespace_expr]):
        raise UnsafeExpressionError(
            "found non-math character in expression", expression
        )

    tree = ast.parse(expression, mode="eval")
    # print(ast.dump(tree, indent=2))

    # Walk through the AST and raise an exception if any illegal ops are found
    for i, node in enumerate(ast.walk(tree)):
        if type(node) is ast.Expression:
            if i == 0 and type(node.body) in LEGAL_AST_NODES:
                # Only an expression that is the first node in the tree and contains a
                # legal AST node in its body is allowed
                continue
            else:
                raise UnsafeExpressionError(
                    (
                        f"at tree index {i}: found invalid Expression node: body type "
                        f"{type(node.body).__name__}"
                    ),
                    expression,
                )
        elif type(node) in LEGAL_AST_NODES:
            continue
        else:
            raise UnsafeExpressionError(
                f"at tree index {i}: found invalid node type: {type(node).__name__}",
                expression,
            )
    return eval(
        compile(tree, "<_safe_arithmetic_eval>", "eval"),
        {"__builtins__": {}},
    )


def resolve_dice_arithmetic(expression: str) -> int | float:
    pure_arithmetic = expression
    for num_dice, num_sides in DICE_RE.findall(pure_arithmetic):
        roll = roll_dice(int(num_dice), int(num_sides))
        to_replace = num_dice + "d" + num_sides
        pure_arithmetic = pure_arithmetic.replace(to_replace, str(roll), 1)

    # An expression just being a single dice roll is a common case
    # Try to return early and skip making an AST if we can
    try:
        return int(pure_arithmetic)
    except:
        pass

    try:
        return _safe_arithmetic_eval(pure_arithmetic)
    except UnsafeExpressionError as e:
        e.add_note(f"original expression: {expression}")
        raise


def is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except:
        return False


def histogram_str(
    dataset: dict[Any, int], max_width=100, sort=True, legend=False
) -> str:
    """Creates a simple text histogram from the `dataset` for easy visualization.

    Assumes that the keys of `dataset` are the domain of the data, and the values are the
    corresponding number of occurences.

    The keys of `histo` *must* support `str()`. If the keys support comparison and `sort`
    is `True`, then the histogram will be created in the sorted order of the keys.
    Otherwise, the data will be printed in the order it is received.

    This function will attempt to keep the total width of the histogram text less than or
    equal to `max_width` by adjusting the value of each "pip" on the right side of the
    histogram. However, if the string representation of the keys takes up a significiant
    portion of the allowed width, then this could badly distort the data visualization.

    If a key contains a non-zero value, but that value is smaller than the value of a
    single pip, rather than displaying nothing the histogram will insert a single
    "piplet".

    Currently a pip is represented by a `*` character, and a piplet by a `.` character.

    # Parameters

    - `dataset`: the dataset to visualize
    - `max_width`: the maximum allowed width for each line of the histogram text
    - `sort`: if True, attempts to create the histogram in key-sorted order
    - `legend`: if True, add a line to the histogram indicating the value of each "pip"
    """
    PIP = "*"
    PIPLET = "."

    if sort:
        try:
            keys = sorted(dataset.keys())
        except:
            keys = list(dataset.keys())
    else:
        keys = list(dataset.keys())

    left_width = max([len(str(key)) for key in keys])
    if legend:
        left_width += 2
    right_width = max_width - left_width

    max_val = max(dataset.values())
    pip_val = max([max_val // right_width, 1])

    if legend:
        lines = [f"{PIP} = {pip_val}"]
    else:
        lines = []

    for key in keys:
        num_pips = round(dataset[key] / pip_val)
        if num_pips > 0:
            pips = PIP * num_pips
        elif dataset[key] > 0:
            pips = PIPLET
        else:
            pips = ""
        lines.append(f"{key:>{left_width}}: {pips}")
    return "\n".join(lines)


# TODO: remove
if __name__ == "__main__":
    # Should print -30.0
    # print(resolve_dice_arithmetic("-(1 + 2 - 3 * 4 / 5 ** 6 // 7) - +(8 + 9 + 10)"))

    # num_dice = 1
    # num_sides = 6
    # histo: dict[int, int] = {i: 0 for i in _dice_range(num_dice, num_sides)}
    # n = 100_000
    # for _ in range(n):
    #     result = int(resolve_dice_arithmetic(f"{num_dice}d{num_sides}"))
    #     histo[result] += 1
    # print(histogram_str(histo, legend=True))

    n = 100_000
    histo: dict[int, int] = {}
    for _ in range(n):
        result = int(resolve_dice_arithmetic(f"10 * (2d6 + 3d10 + 1d20 + 5) - 4"))
        if result in histo:
            histo[result] += 1
        else:
            histo[result] = 1
    print(histogram_str(histo, legend=True))
