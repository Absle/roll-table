import logging
import re
from enum import StrEnum
from pathlib import Path

from roll_table.parsing import roll_column_parse_warning

_logger = logging.getLogger(__name__)

ROLL_RANGE_RE = re.compile(r"(\d+)(-(\d+))?")


class MagicField(StrEnum):
    INDEX = "__index__"
    LINE = "__line__"
    ROLL = "__roll__"


MAGIC_FIELDS = {field.value for field in MagicField}


class Syntax(StrEnum):
    COMMENT = "#"
    DIRECTIVE = "#!"


def parse_roll_range(range_str: str, csv_path: Path, line: int) -> range | None:
    _logger.info("parsing range '%s'", range_str)
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
        roll_column_parse_warning(_logger, csv_path, line, range_str, "failed to match")
        return None
