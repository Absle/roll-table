import copy
import csv
import logging
from pathlib import Path
from random import choice
from typing import Any

from roll_table.logger_adapter import PathLineLogAdapter, extras
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
from roll_table.utils import columnate

# Arbitrary large number, maximum of a 32-bit signed integer
_ROLL_MIN_DEF = 2**31 - 1
# Arbitrary small number, minimum of a 32-bit signed integer
_ROLL_MAX_DEF = -(2**31)

_logger = PathLineLogAdapter(logging.getLogger(__name__))


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
        # Put in default/known values first
        self._path = filepath.absolute()
        self._relative_path = self._path.relative_to(Path.cwd())
        self._roll_expr = None
        self._roll_to_index = dict()
        self._roll_min = _ROLL_MIN_DEF
        self._roll_max = _ROLL_MAX_DEF

        _logger.info("loading table", extra=extras(path=self._relative_path))

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
                _logger.directive_parse_warning(
                    e,
                    self._relative_path,
                    line,
                    directive_str,
                )
                continue

            if type(directive) is IncludeDirective:
                if directive.alias in namespace:
                    # Skip includes with alias collisions
                    _logger.directive_parse_warning(
                        "alias '%s' has already been included",
                        self._relative_path,
                        line,
                        directive_str,
                        directive.alias,
                    )
                    continue

                _logger.info(
                    "including file '%s' as '%s'",
                    str(directive.path.relative_to(Path.cwd())),
                    directive.alias,
                    extra=extras(path=self._relative_path),
                )
                namespace[directive.alias] = directive.path
            else:
                _logger.directive_parse_warning(
                    "unimplemented directive '%s'",
                    self._relative_path,
                    line,
                    directive_str,
                    directive.kind.value,
                )

        line_rows = [
            # Create of raw rows w/ original CSV line numbers
            (i + 1, row)
            for i, row in enumerate(raw_csv)
            if not row.startswith(LineSyntax.COMMENT.value)
        ]
        header_line = line_rows[0][0]

        raw_table = [row.strip() for _, row in line_rows]

        dict_reader = csv.DictReader(
            raw_table, restkey=MagicField.REST.value, restval=""
        )
        self._field_names = list(dict_reader.fieldnames)  # type: ignore
        for field in MagicField:
            self._field_names.append(field.value)

        # Attempt to parse a roll column expression from header
        leftmost = self._field_names[0].strip()
        orig_roll_key = self._field_names[0]
        if leftmost.startswith(ExprSyntax.REPLACE_OPEN.value) and leftmost.endswith(
            ExprSyntax.REPLACE_CLOSE.value
        ):
            _logger.info(
                "parsing dice roll column expression '%s'",
                leftmost,
                extra=extras(path=self._relative_path),
            )

            # Regardless of if it's valid or not, we need to start peeling the dice roll
            # column from the table's field names and rows
            self._field_names.pop(0)

            start = len(ExprSyntax.REPLACE_OPEN.value)
            end = len(leftmost) - len(ExprSyntax.REPLACE_CLOSE.value)
            raw_expr = leftmost[start:end]

            try:
                self._roll_expr = DiceArithExpr(raw_expr, self._path, header_line)
            except ExpressionParseError as e:
                _logger.warning(
                    str(e),
                    extra=extras(
                        path=self._relative_path,
                        line=header_line,
                        when="parsing roll column expression '%s'",
                        effect="parse column will be stripped and ignored",
                        exargs=leftmost,
                    ),
                )
                self._roll_expr = False

        rows = list(dict_reader)
        lines = [line for line, _ in line_rows]
        for index, (line, row) in enumerate(zip(lines[1:], rows)):
            # Add metadata columns to each row
            row[MagicField.INDEX.value] = index
            row[MagicField.LINE.value] = line

            if self._roll_expr is False:
                # Parsing the dice roll column failed at some point, removing the column
                row.pop(orig_roll_key)

            elif self._roll_expr is not None:
                # If there's a roll expression for this table, we need to process those
                # numbers for each table
                range_str = row.pop(orig_roll_key)
                roll_range = parse_roll_range(range_str, self._path, line)

                if roll_range is not None:
                    for roll in roll_range:
                        if roll in self._roll_to_index:
                            _logger.warning(
                                "found roll collision %d",
                                roll,
                                extra=extras(
                                    path=self._relative_path,
                                    line=line,
                                    when="parsing range '%s'",
                                    effect="using existing roll entry",
                                    exargs=range_str,
                                ),
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
                    self._roll_expr = False
                    self._roll_to_index = dict()
                    self._roll_min = _ROLL_MIN_DEF
                    self._roll_max = _ROLL_MAX_DEF

            for field_name in row.keys():
                if field_name in MAGIC_FIELDS or row[field_name] is None:
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
        self, index: int, default: Any | None = None
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
                "rolled %d, which is less than the lowest table value of %d",
                roll,
                self._roll_min,
                extra=extras(path=self._relative_path, effect="using lowest value"),
            )
            index = self._roll_to_index[self._roll_min]

        elif roll > self._roll_max:
            _logger.warning(
                "rolled %d, which is greater than the highest table value of %d",
                roll,
                self._roll_max,
                extra=extras(path=self._relative_path, effect="using highest value"),
            )
            index = self._roll_to_index[self._roll_max]

        else:
            index = 0
            _logger.warning(
                "rolled %d, which is not included in the table",
                roll,
                extra=extras(
                    path=self._relative_path,
                    effect="using default index %d",
                    exargs=index,
                ),
            )
        return self.at_index(index)

    def columnate(self, md_style: bool = False) -> str:
        rows = [[r.get(f, "") for f in self._field_names] for r in self._rows]
        return columnate(
            [self._field_names] + rows, has_headers=True, md_style=md_style
        )

    def roll(self) -> dict[str, str | ReplacementString]:
        if type(self._roll_expr) is DiceArithExpr:
            roll = self._roll_expr.resolve_int()
            rolled = self._at_roll(roll)
        else:
            rolled = choice(self._rows)

        line = int(rolled.get(MagicField.LINE.value, "-1"))  # type: ignore
        _logger.info("rolled line %d", line, extra=extras(path=self._relative_path))
        _logger.debug("%s", repr(rolled), extra=extras(path=self._relative_path))
        return copy.deepcopy(rolled)

    def to_json(self) -> str:
        lines = ["["]
        for i, row in enumerate(self._rows):
            lines.append("  {")
            for j, (k, v) in enumerate(row.items()):
                if type(v) is ReplacementString:
                    v_str = repr(v)
                else:
                    v_str = v
                if j == len(row) - 1:
                    line = f'    "{k}": "{v_str}"'
                else:
                    line = f'    "{k}": "{v_str}",'
                # Handle windows paths
                lines.append(line.replace("\\", "\\\\"))

            if i == len(self._rows) - 1:
                lines.append("  }")
            else:
                lines.append("  },")
        lines.append("]")
        return "\n".join(lines)

    def write_postprocess_csv(self, write_obj):
        writer = csv.DictWriter(write_obj, fieldnames=self._field_names)
        writer.writeheader()
        writer.writerows(self._rows)
