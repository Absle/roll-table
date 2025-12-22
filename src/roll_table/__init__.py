import copy
import csv
import sys
import warnings
from pathlib import Path
from random import choice
from warnings import warn


def _show_warning(message, category, filename, lineno, file=None, line=None):
    if issubclass(category, RollTableWarning):
        s = f"{category.__name__}: {message}"
    else:
        s = f"{filename}:{lineno}: {category.__name__}: {message}"
    print(s, file=sys.stderr)


class ResolveError(Exception):
    def __init__(self, message: str, depth: int, op: str):
        super().__init__(f"pass {depth}: {op}: {message}")


class RollTableWarning(UserWarning):
    def __init__(self, message: str):
        super().__init__(message)


class DirectiveWarning(RollTableWarning):
    def __init__(self, message: str, file: Path, line: int):
        super().__init__(f"{file.absolute()}:{line}: {message}, skipping...")


class IncludeWarning(DirectiveWarning):
    pass


class ResolveWarning(RollTableWarning):
    pass


class FieldResolveWarning(ResolveWarning):
    def __init__(self, message: str, depth: int, op: str):
        super().__init__(f"pass {depth}: {op}: {message}, using first field instead...")


class Table:
    path: Path
    field_names: list[str]
    rows: list[dict]

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
        self.path = Path(filepath).absolute()

        with open(self.path) as csv_file:
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
                            "could not find open and close parens", self.path, line
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
                            f"'{arg_str}' is not a valid file", self.path, line
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
                            self.path,
                            line,
                        )
                    )
                    continue
                namespace[alias] = include_path
            else:
                # Skip invalid directives
                warn(DirectiveWarning("found invalid directive", self.path, line))

        # Pre-processing include replacement aliases
        raw_table = [r for r in raw_csv if not r.startswith(self.COMMENT)]
        for alias, path in namespace.items():
            raw_table = list(
                map(lambda r: r.replace("${" + alias, "${" + str(path)), raw_table)
            )

        dict_reader = csv.DictReader(raw_table)
        self.field_names = list(dict_reader.fieldnames)  # type: ignore
        self.rows = list(dict_reader)

    @property
    def directory(self) -> Path:
        return self.path.parent

    @property
    def filename(self):
        return self.path.name

    def roll(self) -> dict:
        return copy.deepcopy(choice(self.rows))

    def to_json(self) -> str:
        lines = ["["]
        for i, row in enumerate(self.rows):
            lines.append("    {")
            for j, (k, v) in enumerate(row.items()):
                if j == len(row) - 1:
                    line = f'        "{k}": "{v}"'
                else:
                    line = f'        "{k}": "{v}",'
                lines.append(line.replace("\\", "\\\\"))

            if i == len(self.rows) - 1:
                lines.append("    }")
            else:
                lines.append("    },")
        lines.append("]")
        return "\n".join(lines)

    def write_postprocess_csv(self, path: str):
        with open(path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.field_names)
            writer.writeheader()
            for row in self.rows:
                writer.writerow(row)


class TableManager:
    tables: dict[str, Table]

    def __init__(self):
        self.tables = {}

    def add_table(self, path: str):
        table = Table(path)
        self.tables[str(table.path)] = table

    def get_table(self, path: str) -> Table:
        path_key = str(Path(path).absolute())
        if path_key not in self.tables:
            self.add_table(path)
        return self.tables[path_key]

    def resolve(self, rep_str: str, depth_limit: int = 100) -> str:
        for i in range(1, depth_limit + 1):
            if (
                Table.OP_REPLACE_OPEN not in rep_str
                or Table.OP_REPLACE_CLOSE not in rep_str
            ):
                break

            replace_ops: list[str] = []
            cursor = 0
            while cursor < len(rep_str):
                start = rep_str.find(Table.OP_REPLACE_OPEN, cursor)
                cursor = start + len(Table.OP_REPLACE_OPEN)
                end = rep_str.find(Table.OP_REPLACE_CLOSE, cursor)
                cursor = end + len(Table.OP_REPLACE_CLOSE)
                replace_ops.append(rep_str[start : end + 1])

            row: dict | None = None
            replacements: list[str] = []
            for op in replace_ops:
                start = len(Table.OP_REPLACE_OPEN)
                end = op.find(Table.OP_FIELD_OPEN, start)
                if end < 0:
                    end = len(op) - 1
                table_path = op[start:end]

                field = None
                if end != len(op) - 1:
                    start = end + 1
                    end = op.find(Table.OP_FIELD_CLOSE, start)
                    if end < 0:
                        warn(
                            FieldResolveWarning("missing closing field bracket", i, op)
                        )
                    else:
                        field = op[start:end]

                if table_path == Table.OP_PREV_ROW:
                    if row is None:
                        raise (
                            ResolveError(
                                f"'{Table.OP_PREV_ROW}' must not be first replacement",
                                i,
                                op,
                            )
                        )
                else:
                    try:
                        row = self.roll(table_path)
                    except FileNotFoundError as e:
                        extra = ResolveError(f"failed to open file", i, op)
                        e.add_note(f"{type(extra).__name__}: {str(extra)}")
                        raise e

                if field is not None:
                    if field in row:
                        value = row[field]
                    else:
                        warn(FieldResolveWarning("field not in table", i, op))
                        value = next(iter(row.values()))
                else:
                    value = next(iter(row.values()))

                replacements.append(str(value))

            for op, replacement in zip(replace_ops, replacements):
                rep_str = rep_str.replace(op, replacement, 1)
        return rep_str

    def roll(self, table_path: str) -> dict:
        path_key = str(Path(table_path).absolute())
        if path_key not in self.tables:
            self.add_table(table_path)
        return self.tables[path_key].roll()


def main():
    warnings.showwarning = _show_warning
    args = sys.argv
    SELF = args[0]
    USAGE = f"usage: {SELF} <csv_path>"

    if len(args) < 2:
        print(USAGE, file=sys.stderr)
        exit(100)

    csv_path = args[1]
    tm = TableManager()
    try:
        row = tm.roll(csv_path)
    except Exception as e:
        print(f"{type(e).__name__}: {str(e)}", file=sys.stderr)
        exit(101)

    for k, v in row.items():
        if type(v) is str:
            row[k] = tm.resolve(v)

    match len(row):
        case 0:
            print(f"got empty row from '{csv_path}' somehow?", file=sys.stderr)
            exit(102)
        case 1:
            print(next(iter(row.values())))
        case _:
            max_length = max([len(k) for k in row.keys()])
            for k, v in row.items():
                print(f"{k: >{max_length}}: {v}")
    exit(0)


if __name__ == "__main__":
    main()
