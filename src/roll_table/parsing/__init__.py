import logging
from enum import StrEnum
from logging import Logger
from pathlib import Path
from typing import Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from roll_table.parsing.expression import Expression


def _consume(
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


def _parsing_warning(
    logger: Logger, csv_path: Path, line: int, when: str, msg: str | Exception, *args
):
    if logger.getEffectiveLevel() <= logging.WARNING:
        csv_path = csv_path.relative_to(Path.cwd())
        if issubclass(type(msg), Exception):
            msg = str(msg)
        if len(args) > 0:
            msg = msg % args  # type: ignore

        logger.warning("%s:%d: while %s: %s, skipping...", csv_path, line, when, msg)


def directive_parse_warning(
    logger: Logger,
    csv_path: Path,
    line: int,
    directive: str,
    msg: str | Exception,
    *args,
):
    when = f"parsing directive '{directive}'"
    _parsing_warning(logger, csv_path, line, when, msg, *args)


def expression_parse_warning(
    logger: Logger,
    csv_path: Path,
    line: int,
    expression: str,
    msg: str | Exception,
    *args,
):
    when = f"parsing expression '{expression}'"
    _parsing_warning(logger, csv_path, line, when, msg, *args)


def expression_resolve_warning(
    logger, expression: "Expression", msg: str | Exception, *args
):
    when = f"resolving expression '{expression.raw_expr}'"
    _parsing_warning(logger, expression.csv_path, expression.line, when, msg, *args)
