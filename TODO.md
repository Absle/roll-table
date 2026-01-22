# TODO

- different methods for randomizing the row
    - maybe as a `#!dice(2d6)` directive?
    - maybe as a `2d6` column with numbers/ranges in it?
        - this works much better but harder

- some kind of generalized query language? Maybe using `ast.literal_eval`?

- soundboard-like gui? with string replacement fields being re-rollable?
    - slint has a beta python binding

- `#!column_lists` (name?) directive; treat each column in the table as a separate, single-column table that can be indexed into
    - possibly better name: `#!compound_table`

- filtering api for `TableManager.roll` and a new `TableManager.filter`

- Breakout CLI into a separate file and clean up `roll-table/__init__.py` for use as a library

- need a better name for the gui application
    - `town-scryer`?
        - might already be taken by some AI slop product?
    - `scryer`?
    - `table-of-many-things`?
    - `roll-play`?

- need away to make a distributable application for installing
    - [`pyapp`][pyapp-github] seems like the best option and seems to have some kind of [uv integration][pyapp-uv]

- rework all warnings into a proper logging system rather than misusing `warnings.warn`
    - probably also rethink using `errors.py`

- add a `--histogram` option to CLI
    - print a histogram for each field, tracking its occurences

[pyapp-github]: https://github.com/ofek/pyapp
[pyapp-uv]: https://ofek.dev/pyapp/latest/config/installation/#uv

## DONE

- ~~dice rolling and/or math in replacements (`${1d6*10}`)~~
    - ~~update README for this feature now that it's implemented~~
- ~~refactor directive parsing with proper syntax classes~~
- ~~refactor expression parsing and make a proper `ReplacementString` + `Expression` classes for a basic syntax tree~~
