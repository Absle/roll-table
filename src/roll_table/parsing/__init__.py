import logging
from enum import StrEnum
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from roll_table.parsing.expression import Expression


def consume(
    string: str, separators: Sequence[StrEnum]
) -> tuple[str, StrEnum | None, str]:
    """Partition `string` at the first found separator in `separators`.

    # Returns

    - `(left, separator, right)`: for the first separator found, if one was found
    - `(string, None, "")`: if none of the items in `separators` were in `string`
    """
    for separator in separators:
        left, sep, right = string.partition(separator.value)
        if len(sep) > 0:
            return left, separator, right
    return string, None, ""


def parse_warning(
    logger: Logger,
    csv_path: Path,
    line: int,
    when: str,
    msg: str | Exception,
    *args,
    effect=None,
):
    if logger.getEffectiveLevel() <= logging.WARNING:
        csv_path = csv_path.relative_to(Path.cwd())
        if issubclass(type(msg), Exception):
            msg = str(msg)
        if type(msg) is str and len(args) > 0:
            msg = msg % args

        if effect is None:
            effect = "skipping"

        logger.warning("%s:%d: while %s: %s, %s...", csv_path, line, when, msg, effect)


def directive_parse_warning(
    logger: Logger,
    csv_path: Path,
    line: int,
    directive: str,
    msg: str | Exception,
    *args,
):
    when = f"parsing directive '{directive}'"
    parse_warning(logger, csv_path, line, when, msg, *args)


def expression_parse_warning(
    logger: Logger,
    csv_path: Path,
    line: int,
    expression: str,
    msg: str | Exception,
    *args,
):
    when = f"parsing expression '{expression}'"
    parse_warning(logger, csv_path, line, when, msg, *args)


def expression_resolve_warning(
    logger, expression: "Expression", msg: str | Exception, *args
):
    when = f"resolving expression '{expression.raw_expr}'"
    parse_warning(logger, expression.csv_path, expression.line, when, msg, *args)


def roll_column_parse_warning(
    logger: Logger,
    csv_path: Path,
    line: int,
    range_str: str,
    msg: str,
    *args,
    effect: str | None = None,
):
    when = f"parsing range string '{range_str}'"
    if effect is None:
        effect = "parse column will be ignored"
    parse_warning(logger, csv_path, line, when, msg, *args, effect=effect)
