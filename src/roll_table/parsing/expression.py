from enum import StrEnum

ARITHMETIC_START = "+-0123456789("


class Syntax(StrEnum):
    FIELD_OPEN = "["
    FIELD_CLOSE = "]"
    PREV_REF = "~"
    REPLACE_OPEN = "${"
    REPLACE_CLOSE = "}"
