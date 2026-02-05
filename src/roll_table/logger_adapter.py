from logging import LoggerAdapter
from typing import Any, MutableMapping


def extras(
    path: str | None = None,
    line: int | None = None,
    when: str | None = None,
    effect: str | None = None,
    exargs: tuple | None = None,
) -> dict:
    return {
        "path": path,
        "line": line,
        "when": when,
        "effect": effect,
        "exargs": exargs,
    }


class PathLineLogAdapter(LoggerAdapter):
    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        EXTRA = "extra"
        PATH = "path"
        LINE = "line"
        WHEN = "when"
        EFFECT = "effect"
        EXARGS = "exargs"
        if EXTRA not in kwargs:
            # Return early if no extras were sent
            return msg, kwargs

        path = kwargs[EXTRA].get(PATH, None)
        line = kwargs[EXTRA].get(LINE, None)
        when = kwargs[EXTRA].get(WHEN, None)
        effect = kwargs[EXTRA].get(EFFECT, None)
        args = kwargs[EXTRA].get(EXARGS, None)

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

        if args is not None and len(args) > 0:
            processed_msg = processed_msg % args

        # Add message in at the end to preserve non-extra args
        processed_msg = processed_msg.format(msg=msg)
        return processed_msg, kwargs
