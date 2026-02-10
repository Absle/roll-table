from enum import StrEnum
from typing import Sequence


def consume(
    string: str, separators: Sequence[StrEnum]
) -> tuple[str, StrEnum | None, str]:
    """Partition `string` at the first found separator in `separators`.

    # Returns

    - `(left, separator, right)`: for the first separator found, if one was found
    - `(string, None, "")`: if none of the items in `separators` were in `string`
    """
    for separator in separators:
        left, sep, right = string.partition(separator.value)
        if len(sep) > 0:
            return left, separator, right
    return string, None, ""
