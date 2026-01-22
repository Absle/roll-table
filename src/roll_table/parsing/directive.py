from enum import StrEnum, auto
from pathlib import Path

from roll_table.parsing import _consume, line


DIRECTIVE_START = line.Syntax.DIRECTIVE.value


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
        kind = Kind.INCLUDE
        super().__init__(kind)
        self.path = path
        if alias is None:
            self.alias = self.path.stem
        else:
            self.alias = alias

        if not IncludeDirective._is_valid_alias(self.alias):
            raise DirectiveParseError(f"{kind.value}: invalid alias '{self.alias}'")

    @staticmethod
    def _is_valid_alias(alias: str) -> bool:
        return len(alias) > 0 and alias[0].isalpha() or alias[0] in "_"

    @staticmethod
    def _parse(
        prev_separator: StrEnum | None, remaining: str, curr_dir: Path
    ) -> "IncludeDirective":
        kind = Kind.INCLUDE

        if prev_separator is not Syntax.ARG_OPEN:
            raise DirectiveParseError(f"{kind.value}: missing args")

        arg, separator, remaining = _consume(
            remaining, [Syntax.ARG_CLOSE, Syntax.ARG_SEP]
        )
        arg = arg.strip()

        if separator is Syntax.ARG_SEP:
            raise DirectiveParseError(
                f"{kind.value}: too many args, accepts exactly one"
            )
        elif separator is not Syntax.ARG_CLOSE:
            raise DirectiveParseError(
                f"{kind.value}: unclosed args, missing '{Syntax.ARG_CLOSE.value}'"
            )

        path = curr_dir.joinpath(arg).absolute()
        if not path.is_file():
            raise DirectiveParseError(f"{kind.value}: '{arg}' is not a valid path")

        empty, separator, alias = _consume(remaining, [KeyWord.ALIAS])
        alias = alias.strip()
        if len(empty.strip()) != 0:
            raise DirectiveParseError(
                f"{kind.value}: expected '{KeyWord.ALIAS.value} or end of directive, "
                f"found '{empty}'"
            )
        elif separator is None:
            return IncludeDirective(path)
        else:
            return IncludeDirective(path, alias)


def parse_directive(directive_str: str, curr_dir: Path) -> Directive:
    if directive_str.startswith(DIRECTIVE_START):
        directive_str = directive_str[len(DIRECTIVE_START) :]

    name, separator, remaining = _consume(
        directive_str, [Syntax.ARG_OPEN] + list(KeyWord)
    )
    name = name.strip()
    remaining = remaining.strip()
    try:
        kind = Kind[name.upper()]
    except KeyError:
        raise DirectiveParseError(f"unknown directive: '{name}'")

    match kind:
        case Kind.INCLUDE:
            return IncludeDirective._parse(separator, remaining, curr_dir)
        case _:
            raise DirectiveParseError(f"unimplemented parsing for directive '{name}'")
