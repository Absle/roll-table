import datetime
import logging
import os
import re
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from roll_table.parsing.line import MAGIC_FIELDS
from roll_table.table_manager import TableManager
from roll_table.utils import (
    LOG_ENVAR,
    PROG,
    histogram_str,
    try_into_number,
    user_app_log_dir,
)

_logger = logging.getLogger(__name__)


class InvalidFieldError(Exception):
    def __init__(self, csv_path: str, invalid_fields: set):
        invalid_str = ", ".join(invalid_fields)
        super().__init__(
            f"{csv_path} does not have the following fields: {invalid_str}"
        )


def _init_cli_logging(log_arg: str, cleanup: bool = True):
    CONSOLE_LEVEL = logging.WARNING
    CONSOLE_FORMAT = "%(levelname)s: %(message)s"
    LOG_FILE_FORMAT = "%(asctime)s.%(msecs)03d\t%(levelname)-8s\t%(message)s"

    name_to_level = logging.getLevelNamesMapping()
    log_level = name_to_level.get(log_arg.upper(), None)
    if log_level is None and LOG_ENVAR in os.environ:
        log_level = name_to_level.get(os.environ[LOG_ENVAR].upper(), None)

    if log_level is None:
        # No log level set by user, just outputting warnings to console
        logging.basicConfig(level=CONSOLE_LEVEL, format=CONSOLE_FORMAT)
        return

    user_log_root = user_app_log_dir()
    if user_log_root is None:
        # User application logging directory could not be determined for this system
        # Only logging to console
        logging.basicConfig(level=CONSOLE_LEVEL, format=CONSOLE_FORMAT)
        logging.warning(
            "user application log directory could not be determined; logging to console "
            "only"
        )
        return

    # Ensure log directories exist and attempt to create them if not
    log_home = user_log_root.joinpath(PROG + "/logs")
    try:
        log_home.mkdir(parents=True, exist_ok=True)
    except:
        logging.basicConfig(level=CONSOLE_LEVEL, format=CONSOLE_FORMAT)
        logging.warning(
            "failed to find or create application log directory '%s'; logging to console "
            "only",
            str(log_home),
        )
        return

    # Create log file name using a ISO-8601 basic format timestamp
    cli_log_file_fmt = "{}" + f"_{PROG}_cli.log"
    timestamp = datetime.datetime.now().isoformat(timespec="milliseconds")
    timestamp = timestamp.replace("-", "").replace(":", "")
    log_path = log_home.joinpath(cli_log_file_fmt.format(timestamp)).absolute()

    # Ensure log file exists and we have write permissions
    try:
        log_path.touch(exist_ok=True)
        _ = open(log_path, "a")
    except:
        logging.basicConfig(level=CONSOLE_LEVEL, format=CONSOLE_FORMAT)
        logging.warning(
            "failed to create or write to log file '%s', possibly due to a permission "
            "issue; logging to console only",
            str(log_path),
        )
        return

    # Set up logging to file
    datetime.datetime.now().isoformat
    logging.basicConfig(
        level=log_level,
        format=LOG_FILE_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=log_path,
        filemode="a",
    )

    # Log to both log file and console, but in different formats
    console_handler = logging.StreamHandler()
    console_handler.setLevel(CONSOLE_LEVEL)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    logging.getLogger().addHandler(console_handler)

    logging.debug("successfully logging at '%s'", str(log_path))
    print(f"successfully logging at '{log_path}'", file=sys.stderr)
    if not cleanup:
        return

    # Clean up old log files
    log_age_limit = 90  # days
    regex = cli_log_file_fmt.format(r"\d{8}T\d{6}\.\d{3}")
    cli_log_re = re.compile(regex)

    for path in log_home.iterdir():
        if path.is_file() and cli_log_re.fullmatch(path.name) is not None:
            date_str = path.name.partition("T")[0]
            log_date = datetime.date.fromisoformat(date_str)
            delta = datetime.date.today() - log_date

            if delta.days > log_age_limit:
                logging.info(
                    "found log '%s' older than %d days (%d), deleting...",
                    path.name,
                    log_age_limit,
                    delta.days,
                )
                try:
                    path.unlink()
                except:
                    logging.warning("failed to delete old log '%s'", path.name)


def _arg_parser() -> ArgumentParser:
    parser = ArgumentParser(prog=PROG)

    parser.add_argument(
        "--histogram",
        action="store_true",
        help=(
            "print a histogram for each specified field displaying the number of "
            "occurences of each value of the field; recommended to be used with large "
            "values of the --number option"
        ),
    )

    choices = ["debug", "info", "warning", "error", "critical"]
    help = (
        f"enable detailed logging at level {', '.join(choices[:-1])}, or {choices[-1]}; "
        f"overrides environment variable ${LOG_ENVAR}"
    )
    parser.add_argument(
        "--log",
        metavar="LEVEL",
        type=str,
        choices=choices,
        default="",
        help=help,
    )

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


def run(argv: list[str]):
    args = _arg_parser().parse_args(argv)
    _init_cli_logging(args.log)

    tm = TableManager()
    csv_path = Path(args.path)
    table = tm.get_table(csv_path)

    if len(args.fields) > 0:
        # Verify all field names are valid
        invalid_fields = set(args.fields).difference(table.field_names)
        if len(invalid_fields) > 0:
            raise InvalidFieldError(str(csv_path), invalid_fields)
        fields = args.fields
    else:
        fields = [field for field in table.field_names if field not in MAGIC_FIELDS]
    max_length = max([len(field) for field in fields])

    histograms: dict[str, dict[Any, int]] = {}
    for _ in range(args.number):
        row = tm.roll_resolve(csv_path)
        if not args.histogram:
            for field in fields:
                if len(fields) > 1:
                    print(f"{field: >{max_length}}: {row[field]}")
                else:
                    print(f"{row[field]}")

            if len(fields) > 1:
                # Print a blank line between each roll if we're printing multiple fields
                print()
        else:
            for field in fields:
                if field not in histograms:
                    histograms[field] = {}
                if row[field] not in histograms[field]:
                    histograms[field][row[field]] = 1
                else:
                    histograms[field][row[field]] += 1
    if args.histogram:
        for field, histogram in histograms.items():
            print(f"Field: {field}")
            if type(try_into_number(next(iter(histogram.keys())))) is not str:
                sort = "key"
                key_action = try_into_number
            else:
                sort = "count"
                key_action = None
            print(
                histogram_str(histogram, sort=sort, legend=True, key_action=key_action)
            )
            print()


def main():
    try:
        run(sys.argv[1:])
    except Exception as e:
        _logger.critical("%s: %s", type(e).__name__, str(e))
        if hasattr(e, "__notes__"):
            for note in e.__notes__:
                _logger.critical(note, stack_info=True)
        if _logger.getEffectiveLevel() <= logging.DEBUG:
            raise
        exit(1)
    exit(0)


if __name__ == "__main__":
    main()
