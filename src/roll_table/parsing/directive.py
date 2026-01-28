import logging
from enum import StrEnum, auto
from pathlib import Path

from roll_table.parsing import consume, line

DIRECTIVE_START = line.Syntax.DIRECTIVE.value

_logger = logging.getLogger(__name__)


class DirectiveParseError(Exception):
    pass


class Kind(StrEnum):
    INCLUDE = auto()


class KeyWord(StrEnum):
    ALIAS = "as"


class Syntax(StrEnum):
    ARG_OPEN = "("
    ARG_CLOSE = ")"
    ARG_SEP = ","


class Directive:
    _kind: Kind

    def __init__(self, kind: Kind):
        self._kind = kind

    @property
    def kind(self) -> Kind:
        return self._kind


class IncludeDirective(Directive):
    path: Path
    alias: str

    def __init__(self, path: Path, alias: str | None = None):
        if alias is None:
            alias = path.stem

        _logger.debug("path = '%s'", str(path))
        _logger.debug("alias = '%s'", alias)

        if not IncludeDirective._is_valid_alias(alias):
            raise DirectiveParseError(f"invalid alias '{alias}'")

        super().__init__(Kind.INCLUDE)
        self.path = path
        self.alias = alias

    @staticmethod
    def _is_valid_alias(alias: str) -> bool:
        return len(alias) > 0 and alias[0].isalpha() or alias[0] in "_"

    @staticmethod
    def _parse(
        prev_separator: StrEnum | None, remaining: str, curr_dir: Path
    ) -> "IncludeDirective":
        if prev_separator is not Syntax.ARG_OPEN:
            raise DirectiveParseError("missing args")

        arg, separator, remaining = consume(
            remaining, [Syntax.ARG_SEP, Syntax.ARG_CLOSE]
        )
        arg = arg.strip()

        if separator is Syntax.ARG_SEP:
            raise DirectiveParseError("too many args, accepts exactly one")
        elif separator is not Syntax.ARG_CLOSE:
            raise DirectiveParseError(
                f"unclosed args, missing '{Syntax.ARG_CLOSE.value}'"
            )

        path = curr_dir.joinpath(arg).absolute()
        if not path.is_file():
            raise DirectiveParseError(f"'{arg}' is not a valid path")

        empty, separator, alias = consume(remaining, [KeyWord.ALIAS])
        alias = alias.strip()
        empty = empty.strip()
        if len(empty) != 0:
            raise DirectiveParseError(
                f"expected '{KeyWord.ALIAS.value}' or end of directive, found '{empty}'"
            )

        if separator is None:
            include = IncludeDirective(path)
        else:
            include = IncludeDirective(path, alias)
        return include


def parse_directive(directive_str: str, curr_dir: Path) -> Directive:
    if directive_str.startswith(DIRECTIVE_START):
        directive_str = directive_str[len(DIRECTIVE_START) :]

    _logger.info("parsing directive '%s'", directive_str)
    name, separator, remaining = consume(
        directive_str, [Syntax.ARG_OPEN] + list(KeyWord)
    )
    name = name.strip()
    remaining = remaining.strip()
    try:
        kind = Kind[name.upper()]
    except KeyError:
        raise DirectiveParseError(f"unknown directive '{name}'")

    _logger.debug("parsing as %s directive", kind.name)
    match kind:
        case Kind.INCLUDE:
            return IncludeDirective._parse(separator, remaining, curr_dir)
        case _:
            raise DirectiveParseError(f"unimplemented parsing for directive '{name}'")
