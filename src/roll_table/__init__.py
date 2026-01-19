import sys
import warnings
from argparse import ArgumentParser, Namespace

from roll_table.errors import InvalidFieldError, RollTableWarning
from roll_table.parsing.line import MAGIC_FIELDS
from roll_table.table_manager import TableManager

PROG = "roll-table"


def _errout(e: Exception):
    print(f"{PROG}: {type(e).__name__}: {str(e)}", file=sys.stderr)
    if hasattr(e, "__notes__"):
        for note in e.__notes__:
            print(note, file=sys.stderr)
    exit(1)


def _show_warning(message, category, filename, lineno, file=None, line=None):
    if issubclass(category, RollTableWarning):
        s = f"{category.__name__}: {message}"
    else:
        s = f"{filename}:{lineno}: {category.__name__}: {message}"
    print(s, file=sys.stderr)


def _arg_parser() -> ArgumentParser:
    parser = ArgumentParser(prog=PROG)
    parser.add_argument(
        "-n",
        "--number",
        metavar="N",
        type=int,
        default=1,
        help="repeat the specified roll N times",
    )
    parser.add_argument("path", metavar="PATH", type=str, help="path to csv file")
    parser.add_argument(
        "fields",
        metavar="FIELD",
        nargs="*",
        help="space-separated list of field names to print (case-sensitive)",
    )
    return parser


def _main_impl(args: Namespace):
    tm = TableManager()
    csv_path = args.path

    table = tm.get_table(csv_path)
    if len(args.fields) > 0:
        # Verify all field names are valid
        invalid_fields = set(args.fields).difference(table.field_names)
        if len(invalid_fields) > 0:
            raise InvalidFieldError(csv_path, invalid_fields)
        fields = args.fields
    else:
        fields = [field for field in table.field_names if field not in MAGIC_FIELDS]
    max_length = max([len(field) for field in fields])

    for _ in range(args.number):
        row = tm.roll(csv_path)
        for field in fields:
            value = row[field]
            if type(value) is str:
                row[field] = tm.resolve(value)

            if len(fields) > 1:
                print(f"{field: >{max_length}}: {row[field]}")
            else:
                print(f"{row[field]}")

        if len(fields) > 1:
            # Print a blank line between each roll if we're printing multiple fields
            print()


def main():
    warnings.showwarning = _show_warning
    args = _arg_parser().parse_args()
    try:
        _main_impl(args)
    except Exception as e:
        _errout(e)
    exit(0)


if __name__ == "__main__":
    main()
