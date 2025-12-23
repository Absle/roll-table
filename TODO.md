1. dice rolling and/or math in replacements (`${1d6*10}`)
    - one or both of these features could be done as replacements or on cell-based post-processing
    - use python `ast.literal_eval`
2. different methods for randomizing the row
    - maybe as a `#!dice(2d6)` directive?
    - maybe as a `2d6` column with numbers/ranges in it?
3. some kind of generalized query language? Maybe using `ast.literal_eval`?
4. soundboard-like gui? with string replacement fields being re-rollable?
    - slint has a beta python binding