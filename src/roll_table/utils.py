import os
import platform
import random
from pathlib import Path
from typing import Any

PROG = "roll-table"
LOG_ENVAR = "ROLL_TABLE_LOG_LEVEL"


def user_app_log_dir() -> Path | None:
    """Find the user application log directory and return an absolute path to it.

    In order of precedence, this directory is:

    1. The path indicated by envar `XDG_STATE_HOME` if the variable exists, can be parsed
       as a path, and the path is valid.
    2. The path indicated by envar `LocalAppData` if the platform is Windows, the variable
       exists, can be parsed as a path, and the path is valid.
    3. The platform's default directory indicated below if the user's home directory can
       be determined and the path is valid.
        - Windows: `~/AppData/Local`
        - Unix-like: `~/.local/state`
    4. Otherwise, `None` is returned to indicate failure.

    A valid path is one that exists and is a directory, or one that does not exist yet
    and therefore the logging initializer may attempt to create it.
    """
    xdg_envar = os.environ.get("XDG_STATE_HOME", default=None)
    if xdg_envar is not None and Path(xdg_envar).is_dir():
        path_str = xdg_envar
    else:
        if platform.system() == "Windows":
            appdata_envar = os.environ.get("LocalAppData", default=None)
            if appdata_envar is not None:
                path_str = appdata_envar
            else:
                try:
                    # Windows default
                    path_str = str(Path.home().joinpath("AppData/Local").absolute())
                except:
                    # Could not determine home directory for some reason
                    return None
        else:
            try:
                # XDG default
                path_str = str(Path.home().joinpath(".local/state").absolute())
            except:
                # Could not determine home directory for some reason
                return None
    try:
        path = Path(path_str)
    except:
        return None

    if path.is_dir() or not path.exists():
        # It's fine if the logging directory doesn't exist yet, but it's bad if there's a
        # non-directory file there for some reason
        return path
    else:
        return None


def dice_range(num_dice: int, num_sides: int) -> range:
    if num_dice <= 0 or num_sides <= 0:
        return range(0)
    return range(num_dice, num_dice * num_sides + 1)


def roll_dice(num_dice: int, num_sides: int) -> int:
    if num_dice <= 0 or num_sides <= 0:
        return 0
    return sum([random.randint(1, num_sides) for _ in range(num_dice)])


def histogram_str(
    dataset: dict[Any, int], max_width=100, count_sort=False, sort=False, legend=False
) -> str:
    """Creates a simple text histogram from the `dataset` for easy visualization.

    Assumes that the keys of `dataset` are the domain of the data, and the values are the
    corresponding number of occurences. The keys of `dataset` *must* support `str()`.

    If `count_sort` is `True`, the histogram will be created in the sorted order of the
    occurence counts. If the keys support comparison and `sort` is `True`, then the
    histogram will be created in the sorted order of the keys. Otherwise, the data will
    be printed in the order it is received.

    This function will attempt to keep the total width of the histogram text less than or
    equal to `max_width` by adjusting the value of each "pip" on the right side of the
    histogram. However, if the string representation of the keys takes up a significiant
    portion of the allowed width, then this could badly distort the data visualization.

    If a key contains a non-zero value, but that value is smaller than the value of a
    single pip, rather than displaying nothing the histogram will insert a single
    "piplet".

    Currently a pip is represented by a `*` character, and a piplet by a `.` character.

    # Parameters

    - `dataset`: the dataset to visualize
    - `max_width`: the maximum allowed width for each line of the histogram text
    - `count_sort`: if `True`, attempts to create the histogram in count-sorted order;
      overrides `sort` if both are `True`
    - `sort`: if `True`, attempts to create the histogram in key-sorted order
    - `legend`: if `True`, add a line to the histogram indicating the value of each "pip"
    """
    PIP = "*"
    PIPLET = "."

    if count_sort:
        keys = [item[0] for item in sorted(dataset.items(), key=lambda item: item[1])]
    elif sort:
        try:
            keys = sorted(dataset.keys())
        except:
            keys = list(dataset.keys())
    else:
        keys = list(dataset.keys())

    left_width = max([len(str(key)) for key in keys])
    if legend:
        left_width += 2
    right_width = max_width - left_width

    max_val = max(dataset.values())
    pip_val = max([max_val // right_width, 1])

    lines = []
    for key in keys:
        num_pips = round(dataset[key] / pip_val)
        if num_pips > 0:
            pips = PIP * num_pips
        elif dataset[key] > 0:
            pips = PIPLET
        else:
            pips = ""
        lines.append(f"{key:>{left_width}}: {pips}")

    if legend:
        values = dataset.values()
        average = sum(values) / len(values)
        lines.append(
            f"{PIP} = {pip_val}; # of keys = {len(keys)}; avg = {average:.3f}; min = "
            f"{min(values)}; max = {max(values)}"
        )
    return "\n".join(lines)
