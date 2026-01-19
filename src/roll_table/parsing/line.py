from enum import StrEnum


class MagicField(StrEnum):
    INDEX = "__index__"
    LINE = "__line__"


MAGIC_FIELDS = {field.value for field in MagicField}


class Syntax(StrEnum):
    COMMENT = "#"
    DIRECTIVE = "#!"
