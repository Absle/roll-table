from logging import LoggerAdapter
from pathlib import Path
from typing import Any, MutableMapping

EXTRA = "extra"
PATH = "path"
LINE = "line"
WHEN = "when"
EFFECT = "effect"
EXARGS = "exargs"


def extras(
    path: str | Path | None = None,
    line: int | None = None,
    when: str | None = None,
    effect: str | None = None,
    exargs: Any | tuple[Any, ...] | None = None,
) -> dict:
    return {
        PATH: path,
        LINE: line,
        WHEN: when,
        EFFECT: effect,
        EXARGS: exargs,
    }


class PathLineLogAdapter(LoggerAdapter):
    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        # Fits the log message to this template where extra vars are available:
        # [(<path>[:<line>]: ) | (line <line>: )][while <when>, ]<msg>[; <effect>...]

        if EXTRA not in kwargs:
            # Return early if no extras were sent
            return msg, kwargs

        path = kwargs[EXTRA].get(PATH, None)
        if issubclass(type(path), Path):
            path = str(path.absolute().relative_to(Path.cwd()))

        line = kwargs[EXTRA].get(LINE, None)
        when = kwargs[EXTRA].get(WHEN, None)
        effect = kwargs[EXTRA].get(EFFECT, None)
        exargs = kwargs[EXTRA].get(EXARGS, None)

        # Purposely not formatting yet
        processed_msg = "{msg}"

        if when is not None:
            processed_msg = f"while {when}, " + processed_msg

        if path is not None and line is not None:
            processed_msg = f"{path}:{line}: " + processed_msg
        elif path is not None:
            processed_msg = f"{path}: " + processed_msg
        elif line is not None:
            processed_msg = f"line {line}: " + processed_msg

        if effect is not None:
            processed_msg = processed_msg + f"; {effect}..."

        if exargs is not None:
            processed_msg = processed_msg % exargs

        # Need to handle '{}' in args
        processed_msg = processed_msg.replace("{", "<|")
        processed_msg = processed_msg.replace("}", "|>")
        processed_msg = processed_msg.replace("<|msg|>", "{msg}")

        # Format msg in at the end to preserve msg args
        processed_msg = processed_msg.format(msg=msg)

        processed_msg = processed_msg.replace("<|", "{")
        processed_msg = processed_msg.replace("|>", "}")
        return processed_msg, kwargs

    def directive_parse_warning(
        self, msg: str | Exception, path: str | Path, line: int, directive: str, *args
    ):
        when = "parsing directive '%s'"
        effect = "skipping directive"
        self.warning(
            str(msg),
            *args,
            extra=extras(
                path=path, line=line, when=when, effect=effect, exargs=directive
            ),
        )

    def expression_parse_warning(
        self, msg: str | Exception, path: str | Path, line: int, expr: str, *args
    ):
        when = "parsing expression '%s'"
        effect = "skipping expression"
        self.warning(
            str(msg),
            *args,
            extra=extras(path=path, line=line, when=when, effect=effect, exargs=expr),
        )

    def expression_resolve_warning(
        self, msg: str | Exception, path: str | Path, line: int, expr: str, *args
    ):
        when = "resolving expression '%s'"
        effect = "expression can not be resolved"
        self.warning(
            str(msg),
            *args,
            extra=extras(path=path, line=line, when=when, effect=effect, exargs=expr),
        )
