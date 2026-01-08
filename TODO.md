1. ~~dice rolling and/or math in replacements (`${1d6*10}`)~~
    - update README for this feature now that it's implemented
2. different methods for randomizing the row
    - maybe as a `#!dice(2d6)` directive?
    - maybe as a `2d6` column with numbers/ranges in it?
        - this works much better but harder
3. some kind of generalized query language? Maybe using `ast.literal_eval`?
4. soundboard-like gui? with string replacement fields being re-rollable?
    - slint has a beta python binding
5. `#!column_lists` (name?) directive; treat each column in the table as a separate, single-column table that can be indexed into
6. filtering api for `TableManager.roll` and a new `TableManager.filter`
7. Downgrade `ResolveError` to a warning
8. Breakout CLI into a separate file and clean up `roll-table/__init__.py` for use as a library