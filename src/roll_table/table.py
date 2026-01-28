import copy
import csv
import logging
from pathlib import Path
from random import choice

from roll_table.parsing import directive_parse_warning
from roll_table.parsing.directive import (
    DirectiveParseError,
    IncludeDirective,
    parse_directive,
)
from roll_table.parsing.expression import ReplacementString, parse_replacement_string
from roll_table.parsing.line import MAGIC_FIELDS, MagicField
from roll_table.parsing.line import Syntax as LineSyntax

_logger = logging.getLogger(__name__)


class Table:
    _path: Path
    _field_names: list[str]
    _rows: list[dict[str, str | ReplacementString]]

    def __init__(self, filepath: Path):
        _logger.info("loading table '%s'", filepath.absolute().relative_to(Path.cwd()))
        self._path = Path(filepath).absolute()

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

        # Pre-processing include replacement aliases
        line_rows = [
            # Create of raw rows w/ original CSV line numbers
            (i + 1, row)
            for i, row in enumerate(raw_csv)
            if not row.startswith(LineSyntax.COMMENT.value)
        ]

        raw_table = [
            # Add the index and original CSV line number as the last elements of each
            # data line. If it's the header, assign the new columns a magic field name
            (
                row.strip() + f",{i},{line}\n"
                if i != 0
                else row.strip() + f",{MagicField.INDEX},{MagicField.LINE}\n"
            )
            for i, (line, row) in enumerate(line_rows)
        ]

        dict_reader = csv.DictReader(raw_table)
        self._field_names = list(dict_reader.fieldnames)  # type: ignore

        rows = list(dict_reader)
        for row in rows:
            for field_name in row.keys():
                if field_name in MAGIC_FIELDS:
                    continue
                line = int(row[MagicField.LINE])
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

    def roll(self) -> dict[str, str | ReplacementString]:
        rolled = choice(self._rows)
        _logger.debug(
            "rolled '%s' on table '%s'",
            repr(rolled),
            self._path.relative_to(Path.cwd()),
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

    def write_postprocess_csv(self, path: str):
        with open(path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self._field_names)
            writer.writeheader()
            for row in self._rows:
                writer.writerow(row)
