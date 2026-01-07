# `roll-table`

CLI tool and Python library for creating and using libraries of randomization tables, primarily for
role-playing games. Currently only supports plaintext CSV files, the intention being that Excel or
other spreadsheet program is used to create most of the CSV files in any given library.

Supports a simple string replacement language that allows CSV files to reference each other. This
enables greater depth, flexibility, and reusability while creating or borrowing your library of
randomization tables.

## Installation

TODO; right now you would probably have to just build and install from source using `uv`. Other
tools that support the `pyproject.toml` standard may also work.

To install from source, at the root of the repo run this command:

      $ uv tool install --from . roll-table

If you already have it installed, but want to update after a fresh code pull:

      $ uv tool reinstall --from . roll-table

Both of these commands will have `uv` attempt to install a `roll-table` executable somewhere that
is available on your `PATH`. You can see exactly where this is with this command:

      $ uv tool dir --bin

The default install location executables for each OS is documented [here][uv-storage-exe-dir].
Information on customizing install location of the executable can be found
[here][uv-storage-tool-exes]. Information on customizing the Python package install location can be
found [here][uv-storage-tools]. General information on how `uv` handles tools and tool installation
can be found [here][uv-concepts-tools].

[uv-storage-exe-dir]: https://docs.astral.sh/uv/reference/storage/#executable-directory
[uv-storage-tool-exes]: https://docs.astral.sh/uv/reference/storage/#tool-executables
[uv-storage-tools]: https://docs.astral.sh/uv/reference/storage/#tools
[uv-concepts-tools]: https://docs.astral.sh/uv/concepts/tools/#tools

## Creating Tables

Tables are parsed in a line-based fashion, and each line fits into one of the following categories:

1. **Directives:** all lines starting with '`#!`' are treated as directives. See the
   [directives section](#directives) below.

2. **Comments:** all non-directive lines starting with a '`#`' are treated as comments. Comments
   are ignored by the parser, and can be used for the benefit of the table author.

3. **Header:** The first non-directive, non-comment line is treated as the header of the table, and
   is used to assign fieldnames to each column for the rest of the table data. The header is
   **mandatory**, even for simple tables with only one column.

4. **Data:** All other lines in the table are treated as data lines. Internally, data line are
   parsed as dictionaries whose keys are the fieldnames indicated by the header line, and whose
   fields are the contents of the corresponding columns. Columns without corresponding fieldnames
   are ignored by the parser, however empty columns with fieldnames will still have empty strings
   assigned to their fields.

### Directives

Directives are commands performed by the parser before the data portion of the tables is processed.
Directive lines can be place anywhere in the file, but I would suggest placing all of them either
at the very top or the very bottom of the file. See the [style section](#table-style-guide) below.

Because of the difficult nature of quotation marks in CSV files, no directive will ever need
quotation marks in its arguments. Just put the string parameters directly in the parentheses, and
`roll-table` will handle the rest.

Currently the only available directive is the `include` directive, though this may change in the
future.

#### Include Directive

> usage: `#!include(<file_path>)[ as <alias>]`

Makes the table located at `<file_path>` available for string replacements within the current table.
The file path **must be relative** to the current file; file paths with no directories in them will
search in the same directory as the current file. The file path must also use forward slashes as
the path separator.

Included tables are assigned a name for referencing within string replacements. By default this
name is the base file name without the file extension. So for example, `#!include(other.csv)` will
receive the reference name "`other`" and can be referenced in a string replacement like this:
`${other}`. See the [string replacement section](#string-replacement-expressions) for more
information.

You can customize this reference name by adding `as <alias>` to the end of the include line, which
will change the reference name to "`<alias>`". For example, `#!include(other.csv) as another` will
allow you to reference `other.csv` like this: `${another}`.

In the event two or more reference names are the same, the first one included is given priority, and
all subsequent ones are skipped. If you have two included files with the same filename, use aliasing
to give each something more descriptive.

## String Replacement Expressions

String replacement expressions always start with `${` and end on the next found `}`. After the
result of the replacement is, the entire expression (including the `${` and the `}`) are replaced
with the result. Replacement expressions can be embedded inside of larger strings, multiple
replacement expressions can be inside of the same string, and replacement expressions are resolved
recursively.

When using the CLI tool, in order to avoid getting stuck in an infinite loop replacement
expressions will only be recursively resolved to a depth of 100. This is also the default when
using the library API, but can be configured in the parameters.

Replacement expressions are resolved left-to-right, and when recursively resolving string
replacements, subsequent replacment expressions are only resolved *after* existing replacement
expressions, again left-to-right. So for example, say we have the following set of replacement
expressions and results:

| Expression  | Resulting Replacement |
| ----------- | --------------------- |
| `${first}`  | `${fourth} ${fifth}`  |
| `${second}` | 2                     |
| `${third}`  | 3                     |
| `${fourth}` | 4                     |
| `${fifth}`  | 5                     |

Then this string replacement would resolve in the following sequence:

| Step | String                                  |
| ---- | --------------------------------------- |
| 0    | `${first} ${second} ${third}`           |
| 1    | `${fourth} ${fifth} ${second} ${third}` |
| 2    | `${fourth} ${fifth} 2 ${third}`         |
| 3    | `${fourth} ${fifth} 2 3`                |
| 4    | `4 ${fifth} 2 3`                        |
| 5    | `4 5 2 3`                               |

### Syntax

Let's assume we have included a file like so: `#!include(other.csv)`. This results in the default
reference name for this table "`other`".

#### Default Reference

> usage: `${other}`

Roll for a random row from `other.csv` and replace with the field in the leftmost column.

#### Indexed Reference

> usage: `${other[ColumnX]}`

Roll for a random row from `other.csv` and replace with the field beneath the fieldname `ColumnX`.
This allows indexing to specific fields within the row.

#### Previous Reference

> usage: `${~}`

Replace with the field in the leftmost column of the row from the previous roll. So the result of
this will always be from the exact same row of the previous roll, so keep the resolution order in
mind when using this. This only works *within the same string*, so if the first replacement
expression in a string uses `~`, it will fail to resolve.

#### Indexed Previous Reference

> usage: `${~[ColumnX]}`

Replace with the field beneath the fieldname `ColumnX` from the previous roll. Again, the result of
this will always be from the exact same row of the previous roll, so keep the resolution order in
mind when using this.

## Table Style Guide

For most use cases, a consistent style is probably not strictly necessary. However, one
practicality to consider is the placement of directives. For table readability, it is best to place
all directives together at the very top or the very bottom of the file, but there are still some
things to take into consideration when choosing between these two options.

Typical programming convention would place all include directives at the top, and this is slightly
more convenient when editing CSV files. However, one of the advantages of using CSV files is the
interoperability and portability of the format, and many third-party tools used to edit or process
CSV files assume that if there is a header line, then it will always be the first line of the file.
Therefore, it is possible that directives placed at the top of the file will cause more issues with
third-party tools than they would if placed at the bottom.

Speaking from personal experience of using `roll-table` while developing it, I haven't run into
many issues caused by this, but I also only use Excel or OpenOffice Calc to edit my randomization
tables. If you plan on extensively using other third-party tools when building or using your
library, it might be worth considering putting the directives at the bottom.

### The Author's Opinion

This is just generally the style I follow while working on my tables, and most of the examples and
test tables in this repo reflect that.

- Directives at the top
- Use `snake_case` when naming directories, CSV files, and include aliases
- Use `PascalCase` for the fieldnames in the header line to make them stand out a bit visually
