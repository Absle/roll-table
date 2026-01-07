from pathlib import Path


class ResolveError(Exception):
    def __init__(self, message: str, depth: int, op: str):
        super().__init__(f"pass {depth}: {op}: {message}")


class InvalidFieldError(Exception):
    def __init__(self, csv_path: str, invalid_fields: set):
        invalid_str = ", ".join(invalid_fields)
        super().__init__(
            f"{csv_path} does not have the following fields: {invalid_str}"
        )


class UnsafeExpressionError(Exception):
    def __init__(self, message: str, orig_expr: str, math_expr: str):
        self._expr_err_msg = (
            f"while evaluating '{orig_expr}': resolved to '{math_expr}': {message}, "
            "this expression will not be resolved"
        )
        super().__init__(self._expr_err_msg)


class RollTableWarning(UserWarning):
    def __init__(self, message: str):
        super().__init__(message)


class DirectiveWarning(RollTableWarning):
    def __init__(self, message: str, file: Path, line: int):
        super().__init__(f"{file.absolute()}:{line}: {message}, skipping...")


class IncludeWarning(DirectiveWarning):
    pass


class ResolveWarning(RollTableWarning):
    pass


class FieldResolveWarning(ResolveWarning):
    def __init__(self, message: str, depth: int, op: str):
        super().__init__(f"pass {depth}: {op}: {message}, using first field instead...")


class UnsafeExpressionWarning(ResolveWarning):
    def __init__(self, err: UnsafeExpressionError):
        super().__init__(err._expr_err_msg + ", skipping...")
