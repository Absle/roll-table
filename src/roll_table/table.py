import copy
import csv
from enum import Enum
from pathlib import Path
from random import choice
from warnings import warn

from roll_table.errors import IncludeWarning, DirectiveWarning


class Table:
    _path: Path
    _field_names: list[str]
    _rows: list[dict]

    COMMENT = "#"
    DIRECTIVE = COMMENT + "!"
    DIR_INCLUDE = "include"
    OP_ALIAS = "as"
    OP_REPLACE_OPEN = "${"
    OP_REPLACE_CLOSE = "}"
    OP_FIELD_OPEN = "["
    OP_FIELD_CLOSE = "]"
    OP_PREV_ROW = "~"

    def __init__(self, filepath: str):
        self._path = Path(filepath).absolute()

        with open(self._path) as csv_file:
            raw_csv = csv_file.readlines()

        # Pre-processing directives
        namespace = {}
        line_directives = [
            (l, d[len(self.DIRECTIVE) :].strip().strip('"').strip().strip(",").strip())
            for l, d in enumerate(raw_csv)
            if d.strip('"').startswith(self.DIRECTIVE)
        ]
        for i, directive in line_directives:
            line = i + 1

            # Handle include directives
            if directive.startswith(self.DIR_INCLUDE):
                paren_open_idx = len(self.DIR_INCLUDE)
                paren_close_idx = directive.find(")")
                if directive[paren_open_idx] != "(" or paren_close_idx == -1:
                    # Skip includes that don't have parens
                    warn(
                        IncludeWarning(
                            "could not find open and close parens", self._path, line
                        )
                    )
                    continue

                # Pull out path to included file
                arg_str = directive[paren_open_idx + 1 : paren_close_idx]
                include_path = self.directory.joinpath(arg_str).absolute()
                if not include_path.is_file():
                    # Skip includes with paths to invalid or non-existent files
                    warn(
                        IncludeWarning(
                            f"'{arg_str}' is not a valid file", self._path, line
                        )
                    )
                    continue

                rest = directive[paren_close_idx + 1 :].strip()
                if rest.startswith(self.OP_ALIAS + " "):
                    # Grab the word immediately after the alias operator and use as alias
                    alias = rest.split()[1]
                else:
                    alias = include_path.stem

                if alias in namespace:
                    # Skip includes with alias collisions
                    warn(
                        IncludeWarning(
                            f"alias '{alias}' has already been included",
                            self._path,
                            line,
                        )
                    )
                    continue
                namespace[alias] = include_path
            else:
                # Skip invalid directives
                warn(DirectiveWarning("found invalid directive", self._path, line))

        # Pre-processing include replacement aliases
        raw_table = [r for r in raw_csv if not r.startswith(self.COMMENT)]

        # Skip first line to avoid changing headers
        for i in range(1, len(raw_table)):
            for alias, path in namespace.items():
                raw_table[i] = raw_table[i].replace("${" + alias, "${" + str(path))

        dict_reader = csv.DictReader(raw_table)
        self._field_names = list(dict_reader.fieldnames)  # type: ignore
        self._rows = list(dict_reader)

    @property
    def directory(self) -> Path:
        return self._path.parent

    @property
    def field_names(self) -> list[str]:
        return list(self._field_names)

    @property
    def filename(self) -> str:
        return str(self._path.name)

    @property
    def path(self) -> Path:
        return copy.deepcopy(self._path)

    def roll(self) -> dict:
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
