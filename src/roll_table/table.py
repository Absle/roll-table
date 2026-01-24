import copy
import csv
import logging
from pathlib import Path
from random import choice

from roll_table.parsing.directive import (
    DirectiveParseError,
    IncludeDirective,
    parse_directive,
)
from roll_table.parsing.expression import parse_replacement_string, ReplacementString
from roll_table.parsing.line import MAGIC_FIELDS, MagicField, Syntax as LineSyntax
from roll_table.utils import log_parse_warning


_logger = logging.getLogger(__name__)


class Table:
    _path: Path
    _field_names: list[str]
    _rows: list[dict[str, str | ReplacementString]]

    def __init__(self, filepath: Path):
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
                log_parse_warning(_logger, self._path, line, e)
                continue

            if type(directive) is IncludeDirective:
                if directive.alias in namespace:
                    # Skip includes with alias collisions
                    log_parse_warning(
                        _logger,
                        self._path,
                        line,
                        "alias '%s' has already been included",
                        directive.alias,
                    )
                    continue
                namespace[directive.alias] = directive.path
            else:
                log_parse_warning(
                    _logger,
                    self._path,
                    line,
                    "unimplemented directive '%s'",
                    directive.kind.value,
                )

        # Pre-processing include replacement aliases
        line_rows = [
            # Create of raw rows w/ original CSV line numbers
            # f"{line+1}," + row if line != 0 else row
            (i + 1, row)
            for i, row in enumerate(raw_csv)
            if not row.startswith(LineSyntax.COMMENT.value)
        ]

        raw_table = [
            # Add the index and original CSV line number as the first elements of each
            # data line. If it's the header, assign new columns a magic field name
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
                row[field_name] = parse_replacement_string(row[field_name], namespace)
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
        return copy.deepcopy(choice(self._rows))

    def to_json(self) -> str:
        lines = ["["]
        for i, row in enumerate(self._rows):
            lines.append("    {")
            for j, (k, v) in enumerate(row.items()):
                if j == len(row) - 1:
                    line = f'        "{k}": "{v}"'
                else:
                    line = f'        "{k}": "{v}",'
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
