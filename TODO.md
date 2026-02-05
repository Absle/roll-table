# TODO

## Bugs

- bug: if the number of columns in a row isn't the same as the header, then the `__index__` and/or `__line__` can get back filled with `None` because that's how `DictReader` treats empty fields
    - fix: add magic fields `_field_names` and to each row after `DictReader` is already done
    - related: might have similar issues if there are too many fields in a data row? check it out while working on this

## Features/Changes

### Backend

- dice roll column: put expression in header of leftmost column and number range in the rows to affect how rows are chosen

- update logging to use `LogAdapter`
    - use to make `<filepath>:<lineno>: <while>: <msg>; <effect>...` style logs have cleaner code
    - relevant [documentation][logger-adapter-doc] and [cookbook][logger-adapter-cookbook]

- `#!compound_table` directive: treat each column in the table as a separate, single-column table that can be indexed into

- implement shorthand replacements, i.e. `${option1|option2}`

- filtering api for `TableManager.roll` and a new `TableManager.filter`

[logger-adapter-doc]: <https://docs.python.org/3/library/logging.html#logging.LoggerAdapter>
[logger-adapter-cookbook]: <https://docs.python.org/3/howto/logging-cookbook.html#adding-contextual-information-to-your-logging-output>

### GUI

- soundboard-like gui? with string replacement fields being re-rollable?
    - slint has a beta python binding

## Documentation

- update readme for dice roll columns

- start adding docstrings to interface functions

## Testing

- actually start testing? at least unit tests? please?

## Misc

- need a way to make a distributable application for installing
    - [`pyapp`][pyapp-github] seems like the best option and seems to have some kind of [uv integration][pyapp-uv]

- need a better name for the gui application
    - `town-scryer`
        - might already be taken by some AI slop product?
    - `scryer`
    - `table-of-many-things`
    - `roll-play`
    - `role-table`
    - `elder-rolls`

- some kind of generalized query language? Maybe using `ast.literal_eval`?
    - `ast.literal_eval` doesn't even remotely work like this
    - is this even needed anymore?

[pyapp-github]: https://github.com/ofek/pyapp
[pyapp-uv]: https://ofek.dev/pyapp/latest/config/installation/#uv

---

## **DONE**

- ~~Breakout CLI into a separate file and clean up `roll-table/__init__.py` for use as a library~~
- ~~add a `--histogram` option to CLI~~
    - ~~print a histogram for each field, tracking its occurences~~
- ~~rework all warnings into a proper logging system rather than misusing `warnings.warn`~~
    - ~~probably also rethink using `errors.py` [removed it]~~
    - ~~write new warnings for expression parsing and any other missing areas~~
    - ~~write info and debug logs for table parsing, rolling, and resolving~~
    - ~~add CLI option for changing log level~~
    - ~~add envar for configure log level~~
- ~~refactor expression parsing and make a proper `ReplacementString` + `Expression` classes for a basic syntax tree~~
- ~~refactor directive parsing with proper syntax classes~~
- ~~dice rolling and/or math in replacements (`${1d6*10}`)~~
    - ~~update README for this feature now that it's implemented~~
