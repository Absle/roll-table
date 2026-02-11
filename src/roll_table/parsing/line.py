import logging
import re
from enum import StrEnum
from pathlib import Path

from roll_table.logger_adapter import PathLineLogAdapter, extras

_logger = PathLineLogAdapter(logging.getLogger(__name__))


ROLL_RANGE_RE = re.compile(r"(\d+)(-(\d+))?")


class MagicField(StrEnum):
    REST = "__rest__"
    INDEX = "__index__"
    LINE = "__line__"


MAGIC_FIELDS = {field.value for field in MagicField}


class Syntax(StrEnum):
    COMMENT = "#"
    DIRECTIVE = "#!"


def parse_roll_range(range_str: str, csv_path: Path, line: int) -> range | None:
    _logger.info(
        "parsing range '%s'", range_str, extra=extras(path=csv_path, line=line)
    )

    # Remove all whitespace
    range_str = "".join(range_str.split())
    fullmatch = ROLL_RANGE_RE.fullmatch(range_str)
    if fullmatch is not None:
        groups = fullmatch.groups()
        start = int(groups[0])
        if groups[2] is not None:
            end = int(groups[2])
            return range(start, end + 1)
        else:
            return range(start, start + 1)
    else:
        _logger.warning(
            "range does not match expected syntax",
            extra=extras(
                path=csv_path,
                line=line,
                when="parsing range '%s'",
                effect="dice roll column will be removed and ignored",
                exargs=range_str,
            ),
        )
        return None
