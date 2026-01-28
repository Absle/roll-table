import datetime
import logging
import os
import re
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from roll_table.parsing.line import MAGIC_FIELDS
from roll_table.table_manager import TableManager
from roll_table.utils import LOG_ENVAR, PROG, user_app_log_dir


class InvalidFieldError(Exception):
    def __init__(self, csv_path: str, invalid_fields: set):
        invalid_str = ", ".join(invalid_fields)
        super().__init__(
            f"{csv_path} does not have the following fields: {invalid_str}"
        )


def _init_cli_logging(log_level: int | None, cleanup: bool = True):
    console_level = logging.WARNING
    console_format = "%(levelname)s: %(message)s"
    log_file_format = "%(asctime)s.%(msecs)03d\t%(levelname)-8s\t%(message)s"

    if log_level is None:
        # No log level set by user, just outputting warnings to console
        logging.basicConfig(level=console_level, format=console_format)
        return

    user_log_root = user_app_log_dir()
    if user_log_root is None:
        # User application logging directory could not be determined for this system
        # Only logging to console
        logging.basicConfig(level=console_level, format=console_format)
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
        logging.basicConfig(level=console_level, format=console_format)
        logging.warning(
            "failed to find or create application log directory '%s'; logging to console "
            "only",
            str(log_home),
        )
        return

    # Ensure log file exists and we have write permissions
    cli_log_file_fmt = "{}" + f"_{PROG}_cli.log"
    now = datetime.datetime.now().isoformat().replace(":", "-").replace(".", "_")
    log_path = log_home.joinpath(cli_log_file_fmt.format(now)).absolute()
    try:
        log_path.touch(exist_ok=True)
        _ = open(log_path, "a")
    except:
        logging.basicConfig(level=console_level, format=console_format)
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
        format=log_file_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=str(log_path),
        filemode="a",
    )

    # Log to both log file and console, but in different formats
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(console_format))
    logging.getLogger().addHandler(console_handler)

    logging.debug("successfully logging at '%s'", str(log_path))
    print(f"successfully logging at '{log_path}'", file=sys.stderr)
    if not cleanup:
        return

    # Clean up old log files
    log_age_limit = 90  # days
    regex = cli_log_file_fmt.format(r"\d\d\d\d-\d\d-\d\dT\d\d-\d\d-\d\d_\d+")
    cli_log_re = re.compile(regex)
    today = datetime.date.today().isoformat()
    for file_path in log_home.iterdir():
        file_name = file_path.name
        if file_path.is_file() and cli_log_re.fullmatch(file_name) is not None:
            date_str = file_name[0 : len(today)]
            log_date = datetime.date.fromisoformat(date_str)
            delta = datetime.date.today() - log_date
            if delta.days > log_age_limit:
                logging.info(
                    "found log '%s' older than %d days, deleting...",
                    file_name,
                    log_age_limit,
                )
                try:
                    file_path.unlink()
                except:
                    logging.warning("failed to delete old log '%s'", file_name)


def _arg_parser() -> ArgumentParser:
    parser = ArgumentParser(prog=PROG)

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


def _main_impl(args: Namespace):
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

    for _ in range(args.number):
        row = tm.roll_resolve(csv_path)
        for field in fields:
            if len(fields) > 1:
                print(f"{field: >{max_length}}: {row[field]}")
            else:
                print(f"{row[field]}")

        if len(fields) > 1:
            # Print a blank line between each roll if we're printing multiple fields
            print()


def main():
    args = _arg_parser().parse_args()

    log_arg = None
    if args.log is not None:
        log_arg = args.log.upper()
    elif os.environ.get(LOG_ENVAR, default=None) is not None:
        log_arg = os.environ[LOG_ENVAR].upper()
    log_level = logging.getLevelNamesMapping().get(log_arg, None)  # type: ignore

    _init_cli_logging(log_level)
    logger = logging.getLogger(__name__)

    try:
        _main_impl(args)
    except Exception as e:
        logger.critical("%s: %s", type(e).__name__, str(e))
        if hasattr(e, "__notes__"):
            for note in e.__notes__:
                logger.critical(note)
        exit(1)
    exit(0)


if __name__ == "__main__":
    main()
