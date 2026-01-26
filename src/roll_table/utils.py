import os
import random
from pathlib import Path
from typing import Any


PROG = "roll-table"
SYS_LOG_HOME = os.environ.get("XDG_STATE_HOME", default=None)
if SYS_LOG_HOME is None:
    try:
        import platform

        if platform.system() == "Windows":
            SYS_LOG_HOME = os.environ.get("LocalAppData", default=None)
            if SYS_LOG_HOME is None:
                SYS_LOG_HOME = str(Path.home().joinpath("AppData/Local").absolute())
        else:
            SYS_LOG_HOME = str(Path.home().joinpath(".local/state").absolute())
    except:
        SYS_LOG_HOME = None


def dice_range(num_dice: int, num_sides: int) -> range:
    if num_dice <= 0 or num_sides <= 0:
        return range(0)
    return range(num_dice, num_dice * num_sides + 1)


def roll_dice(num_dice: int, num_sides: int) -> int:
    if num_dice <= 0 or num_sides <= 0:
        return 0
    return sum([random.randint(1, num_sides) for _ in range(num_dice)])


def histogram_str(
    dataset: dict[Any, int], max_width=100, sort=True, legend=False
) -> str:
    """Creates a simple text histogram from the `dataset` for easy visualization.

    Assumes that the keys of `dataset` are the domain of the data, and the values are the
    corresponding number of occurences.

    The keys of `histo` *must* support `str()`. If the keys support comparison and `sort`
    is `True`, then the histogram will be created in the sorted order of the keys.
    Otherwise, the data will be printed in the order it is received.

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
    - `sort`: if True, attempts to create the histogram in key-sorted order
    - `legend`: if True, add a line to the histogram indicating the value of each "pip"
    """
    PIP = "*"
    PIPLET = "."

    if sort:
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

    if legend:
        lines = [f"{PIP} = {pip_val}"]
    else:
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
    return "\n".join(lines)


# TODO: remove
if __name__ == "__main__":
    from roll_table.parsing.expression import DiceArithExpr

    # Should print -30.0
    # print(resolve_dice_arithmetic("-(1 + 2 - 3 * 4 / 5 ** 6 // 7) - +(8 + 9 + 10)"))

    # num_dice = 1
    # num_sides = 6
    # histo: dict[int, int] = {i: 0 for i in _dice_range(num_dice, num_sides)}
    # n = 100_000
    # for _ in range(n):
    #     result = int(resolve_dice_arithmetic(f"{num_dice}d{num_sides}"))
    #     histo[result] += 1
    # print(histogram_str(histo, legend=True))

    n = 100_000
    histo: dict[int, int] = {}
    expr = DiceArithExpr("10 * (2d6 + 3d10 + 1d20 + 5) - 4", Path("__main__.csv"), 0)
    for _ in range(n):
        result = int(expr._resolve())
        if result in histo:
            histo[result] += 1
        else:
            histo[result] = 1
    print(histogram_str(histo, legend=True))
