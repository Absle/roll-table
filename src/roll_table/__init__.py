import sys
import warnings

from roll_table.errors import RollTableWarning
from roll_table.table_manager import TableManager


def _errout(s: str):
    print(s, file=sys.stderr)


def _show_warning(message, category, filename, lineno, file=None, line=None):
    if issubclass(category, RollTableWarning):
        s = f"{category.__name__}: {message}"
    else:
        s = f"{filename}:{lineno}: {category.__name__}: {message}"
    _errout(s)


def main():
    warnings.showwarning = _show_warning
    args = sys.argv
    SELF = args[0]
    USAGE = f"usage: {SELF} <csv_path>"

    if len(args) < 2:
        _errout(USAGE)
        exit(100)

    csv_path = args[1]
    tm = TableManager()
    try:
        row = tm.roll(csv_path)
    except Exception as e:
        _errout(f"{type(e).__name__}: {str(e)}")
        exit(101)

    for k, v in row.items():
        if type(v) is str:
            row[k] = tm.resolve(v)

    match len(row):
        case 0:
            _errout(f"got empty row from '{csv_path}'")
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
