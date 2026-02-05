import copy
import csv
import logging
from pathlib import Path
from random import choice
from typing import Any

from roll_table.parsing import (
    directive_parse_warning,
    parse_warning,
    roll_column_parse_warning,
)
from roll_table.parsing.directive import (
    DirectiveParseError,
    IncludeDirective,
    parse_directive,
)
from roll_table.parsing.expression import (
    DiceArithExpr,
    ExpressionParseError,
    ReplacementString,
)
from roll_table.parsing.expression import Syntax as ExprSyntax
from roll_table.parsing.expression import parse_replacement_string
from roll_table.parsing.line import MAGIC_FIELDS, MagicField
from roll_table.parsing.line import Syntax as LineSyntax
from roll_table.parsing.line import parse_roll_range

# Arbitrary large number, maximum of a 32-bit signed integer
_ROLL_MIN_DEF = 2**31 - 1
# Arbitrary small number, minimum of a 32-bit signed integer
_ROLL_MAX_DEF = -(2**31)

_logger = logging.getLogger(__name__)


class Table:
    _path: Path
    _relative_path: Path
    _field_names: list[str]
    _rows: list[dict[str, str | ReplacementString]]
    # None if there is no dice roll column, DiceArithExpr if there is a dice roll column
    # and it loads successfully, False if there is a dice roll column but it fails to
    # parse for some reason
    _roll_expr: DiceArithExpr | bool | None
    _roll_to_index: dict[int, int]
    _roll_min: int
    _roll_max: int

    def __init__(self, filepath: Path):
        _logger.info("loading table '%s'", filepath.absolute().relative_to(Path.cwd()))

        # Put in default/known values first
        self._path = Path(filepath).absolute()
        self._relative_path = self._path.relative_to(Path.cwd())
        self._roll_expr = None
        self._roll_to_index = dict()
        self._roll_min = _ROLL_MIN_DEF
        self._roll_max = _ROLL_MAX_DEF

        with open(self._path) as csv_file:
            raw_csv = csv_file.readlines()

        # Pre-processing directives
        namespace: dict[str, Path] = {}
        line_directives = [
            (
                l + 1,
                d.strip().strip(",").strip('"').strip(),
            )
            for l, d in enumerate(raw_csv)
            if d.strip('"').startswith(LineSyntax.DIRECTIVE.value)
        ]
        for line, directive_str in line_directives:
            try:
                directive = parse_directive(directive_str, self.directory)
            except DirectiveParseError as e:
                directive_parse_warning(_logger, self._path, line, directive_str, e)
                continue

            if type(directive) is IncludeDirective:
                if directive.alias in namespace:
                    # Skip includes with alias collisions
                    directive_parse_warning(
                        _logger,
                        self._path,
                        line,
                        directive_str,
                        "alias '%s' has already been included",
                        directive.alias,
                    )
                    continue
                _logger.info(
                    "including file '%s' as '%s'",
                    directive.path.relative_to(Path.cwd()),
                    directive.alias,
                )
                namespace[directive.alias] = directive.path
            else:
                directive_parse_warning(
                    _logger,
                    self._path,
                    line,
                    directive_str,
                    "unimplemented directive '%s'",
                    directive.kind.value,
                )

        line_rows = [
            # Create of raw rows w/ original CSV line numbers
            (i + 1, row)
            for i, row in enumerate(raw_csv)
            if not row.startswith(LineSyntax.COMMENT.value)
        ]
        header_line = line_rows[0][0]

        raw_table = [
            # Add the index and original CSV line number as the last elements of each
            # data line. If it's the header, assign the new columns a magic field name
            (
                row.strip() + f",{i-1},{line}\n"
                if i != 0
                else row.strip() + f",{MagicField.INDEX},{MagicField.LINE}\n"
            )
            for i, (line, row) in enumerate(line_rows)
        ]

        dict_reader = csv.DictReader(raw_table)
        self._field_names = list(dict_reader.fieldnames)  # type: ignore

        # Attempt to parse a roll column expression from header
        leftmost = self._field_names[0].strip()
        orig_roll_key = self._field_names[0]
        if leftmost.startswith(ExprSyntax.REPLACE_OPEN.value) and leftmost.endswith(
            ExprSyntax.REPLACE_CLOSE.value
        ):
            _logger.info("parsing dice roll column expression '%s'", leftmost)

            # Regardless of if it's valid or not, we need to start peeling the dice roll
            # column from the table's field names and rows
            self._field_names.pop(0)

            start = len(ExprSyntax.REPLACE_OPEN.value)
            end = len(leftmost) - len(ExprSyntax.REPLACE_CLOSE.value)
            raw_expr = leftmost[start:end]

            try:
                self._roll_expr = DiceArithExpr(raw_expr, self._path, header_line)
            except ExpressionParseError as e:
                parse_warning(
                    logger=_logger,
                    csv_path=self._path,
                    line=header_line,
                    when=f"parsing roll column expression '{leftmost}'",
                    msg=e,
                    effect="parse column will be ignored",
                )
                self._roll_expr = False

        rows = list(dict_reader)
        for index, row in enumerate(rows):
            line = int(row.get(MagicField.LINE.value, "-1"))
            if self._roll_expr is False:
                # Parsing the dice roll column failed at some point, removing the column
                row.pop(orig_roll_key)

            elif self._roll_expr is not None:
                # If there's a roll expression for this table, we need to process those number
                # numbers for each table
                # orig_roll_field should always be bound if self._roll_expr is not None
                range_str = row.pop(orig_roll_key)
                roll_range = parse_roll_range(range_str, self._path, line)

                if roll_range is not None:
                    for roll in roll_range:
                        if roll in self._roll_to_index:
                            roll_column_parse_warning(
                                _logger,
                                self._path,
                                line,
                                range_str,
                                "found roll collision %d",
                                roll,
                                effect="using existing entry",
                            )
                            continue
                        self._roll_to_index[roll] = index

                        # Keep track of the mins and maxes to handle cases where the dice
                        # roll column expression gives numbers outside of the ranges
                        # provided by user
                        if self._roll_min > roll:
                            self._roll_min = roll
                        if self._roll_max < roll:
                            self._roll_max = roll
                else:
                    # Dice roll column parse has failed, need to start removing the column
                    # reset everything back to its default
                    # TODO: it feels like there should be something else to do here?
                    self._roll_expr = False
                    self._roll_to_index = dict()
                    self._roll_min = _ROLL_MIN_DEF
                    self._roll_max = _ROLL_MAX_DEF

            for field_name in row.keys():
                if field_name in MAGIC_FIELDS:
                    continue
                row[field_name] = parse_replacement_string(
                    row[field_name], namespace, self._path, line
                )
        self._rows = rows

    @property
    def directory(self) -> Path:
        return self._path.parent

    @property
    def field_names(self) -> list[str]:
        return list(self._field_names)

    @property
    def filename(self) -> str:
        return self._path.name

    @property
    def path(self) -> Path:
        return copy.deepcopy(self._path)

    def at_index(
        self, index: int, default: Any = None
    ) -> dict[str, str | ReplacementString] | Any:
        if index < 0 or index >= len(self._rows):
            return default
        else:
            return self._rows[index]

    def _at_roll(self, roll: int) -> dict[str, str | ReplacementString]:
        if roll in self._roll_to_index:
            index = self._roll_to_index[roll]
        elif roll < self._roll_min:
            _logger.warning(
                "%s: rolled below minimum %d: %d; using minimum...",
                self._relative_path,
                self._roll_min,
                roll,
            )
            index = self._roll_to_index[self._roll_min]
        elif roll > self._roll_max:
            _logger.warning(
                "%s: rolled above maximum %d: %d; using maximum...",
                self._relative_path,
                self._roll_max,
                roll,
            )
            index = self._roll_to_index[self._roll_max]
        else:
            index = 0
            _logger.warning(
                "%s: rolled number not covered in dice roll column: %d; using index %d",
                self._relative_path,
                roll,
                index,
            )
        return self.at_index(index)

    def roll(self) -> dict[str, str | ReplacementString]:
        if type(self._roll_expr) is DiceArithExpr:
            roll = self._roll_expr.resolve_int()
            rolled = self._at_roll(roll)
        else:
            rolled = choice(self._rows)

        line = int(rolled.get(MagicField.LINE.value, "-1"))  # type: ignore
        _logger.info("rolled %s:%d", self._relative_path, line)
        _logger.debug(
            "rolled %s on '%s'",
            repr(rolled),
            self._relative_path,
        )
        return copy.deepcopy(rolled)

    def to_json(self) -> str:
        lines = ["["]
        for i, row in enumerate(self._rows):
            lines.append("    {")
            for j, (k, v) in enumerate(row.items()):
                if type(v) is ReplacementString:
                    v_str = repr(v)
                else:
                    v_str = v
                if j == len(row) - 1:
                    line = f'        "{k}": "{v_str}"'
                else:
                    line = f'        "{k}": "{v_str}",'
                # Handle windows paths
                lines.append(line.replace("\\", "\\\\"))

            if i == len(self._rows) - 1:
                lines.append("    }")
            else:
                lines.append("    },")
        lines.append("]")
        return "\n".join(lines)

    def write_postprocess_csv(self, write_obj):
        writer = csv.DictWriter(write_obj, fieldnames=self._field_names)
        writer.writeheader()
        for row in self._rows:
            writer.writerow(row)
