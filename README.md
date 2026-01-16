# `roll-table`

CLI tool and Python library for creating and using libraries of randomization tables, primarily for role-playing games. Currently only supports plaintext CSV files, the intention being that Excel or other spreadsheet program is used to create most of the CSV files in any given library.

Supports a simple string replacement language that allows CSV files to reference each other. This enables greater depth, flexibility, and reusability while creating or borrowing your library of randomization tables.

## Installation

TODO; right now you would probably have to just build and install from source using `uv`. Other tools that support the `pyproject.toml` standard may also work.

To install from source, at the root of the repo run this command:

      $ uv tool install --from . roll-table

If you already have it installed, but want to update after a fresh code pull:

      $ uv tool reinstall --from . roll-table

Both of these commands will have `uv` attempt to install a `roll-table` executable somewhere that is available on your `PATH`. You can see exactly where this is with this command:

      $ uv tool dir --bin

The default install location executables for each OS is documented [here][uv-storage-exe-dir]. Information on customizing install location of the executable can be found [here][uv-storage-tool-exes]. Information on customizing the Python package install location can be found [here][uv-storage-tools]. General information on how `uv` handles tools and tool installation can be found [here][uv-concepts-tools].

[uv-storage-exe-dir]: https://docs.astral.sh/uv/reference/storage/#executable-directory
[uv-storage-tool-exes]: https://docs.astral.sh/uv/reference/storage/#tool-executables
[uv-storage-tools]: https://docs.astral.sh/uv/reference/storage/#tools
[uv-concepts-tools]: https://docs.astral.sh/uv/concepts/tools/#tools

## Creating Tables

Tables are parsed in a line-based fashion, and each line fits into one of the following categories:

1. **Directives:** all lines starting with '`#!`' are treated as directives. See the [directives section](#directives) for more info.

2. **Comments:** all non-directive lines starting with a '`#`' are treated as comments. Comments are ignored by the parser, and can be used for the benefit of the table author.

3. **Header:** The first non-directive, non-comment line is treated as the header of the table, and is used to assign field names to each column for the rest of the table data. The header is **mandatory**, even for simple tables with only one column.

4. **Data:** All other lines in the table are treated as data lines. Internally, data lines are parsed as dictionaries whose keys are the field names indicated by the header line, and whose fields are the contents of the corresponding columns. Columns without corresponding field names are ignored by the parser, however empty columns with field names will still have empty strings assigned to those fields.

### Directives

Directives are commands performed by the parser before the data portion of the tables is processed. Directive lines can be place anywhere in the file, but I would suggest placing all of them either at the very top or the very bottom of the file. See the [style guide section](#table-style-guide) for more info.

Because of the difficult nature of quotation marks in CSV files, no directive will ever need quotation marks in its arguments. Just put the string parameters directly in the parentheses, and `roll-table` will handle the rest.

Currently the only available directive is the `include` directive, though this may change in the future.

#### Include Directive

> usage: `#!include(<file_path>)[ as <alias>]`

Makes the table located at `<file_path>` available for string replacement expressions within the current table. The path *must be relative* to the directory of the current file; paths with no directories in them will search in the same directory as the current file. The file path must also use forward slashes (`/`) as the path separator.

Each included table is assigned an alias for use in reference expressions. By default this alias is the base file name without the file extension (a.k.a. the file's "stem"). For example, `#!include(other.csv)` will receive the alias "other" and can be used in a reference expression like this: `${other}`. 

You can customize this alias by adding the optional `... as <alias>` clause to the end of the include directive, which will change the alias to "`<alias>`". For example, `#!include(other.csv) as another` will force the tables alias to "another" and can be used in a reference expression like this: `${another}`.

If more than one include directive resolves to the same alias, the first include directive is given priority, and all the others are skipped. If you need to include two different files with the same stem, use the `as` clause to avoid collision.

See the [reference expressions section](#reference-expressions) for more info on how to use included tables.

## String Replacement Expressions

There are currently two kinds of expressions:

1. [Reference expressions](#reference-expressions)
2. [Dice-arithmetic expressions](#dice-arithmetic-expressions)

With just these two kinds of expressions, string replacement expressions are able to support the following:

- Reference data from a random row of another table using reference expressions
- Reuse the same row from the previous reference expression
- Resolve dice rolls to get random integers using dice operations
- Use those random dice rolls to and other numbers in basic arithemetic operations.

For example, after resolving all the replacement expressions in this string,

      You find a ${encounter[Type]} named ${~[FirstName]} ${~[LastName]} carrying ${2d10+5} gold.

you might end up with:

> You find a goblin named Billy Bob carrying 25 gold.

Assuming you had [included](#include-directive) a table named "encounter" that at least had the fields "Type", "FirstName" and "LastName".

Replacement expressions always start with `${` and end on the next found `}`. After the expression is resolved, the entire expression (including the `${` and the `}`) is replaced with the result. Replacement expressions can be embedded inside of larger strings, multiple expressions can be inside of the same string, and expressions are resolved recursively.

When using the CLI tool, in order to avoid getting stuck in an infinite loop, replacement expressions will only be recursively resolved to a depth of 100. This is also the default behavior when using the library API, but can be configured in the parameters.

### Resolution Order

Replacement expressions are resolved left-to-right. When recursively resolving expressions, subsequent expressions are only resolved *after* existing expressions, again left-to-right. So for example, say we have the following set of replacement expressions and results:

| Expression  | Resulting Replacement |
| ----------- | --------------------- |
| `${first}`  | `${fourth} ${fifth}`  |
| `${second}` | `2`                   |
| `${third}`  | `3`                   |
| `${fourth}` | `4`                   |
| `${fifth}`  | `5`                   |

Then the string "`${first} ${second} ${third}`" would resolve all of its replacement expressions in the following sequence:

| Step | String                                  |
| ---- | --------------------------------------- |
| 0    | `${first} ${second} ${third}`           |
| 1    | `${fourth} ${fifth} ${second} ${third}` |
| 2    | `${fourth} ${fifth} 2 ${third}`         |
| 3    | `${fourth} ${fifth} 2 3`                |
| 4    | `4 ${fifth} 2 3`                        |
| 5    | `4 5 2 3`                               |

### Recursive vs. Nested Expressions

Although recursive expressions (expressions which result in more expressions) are allowed, *nested* expressions (expressions inside of other expressions) are not. You may think to try something clever likes this:

      ${some_table[${random_index}]}

Unfortunately, currently this will result in an error at best, and undefined behavior at worst.

The resolver treats the first closing '`}`' it finds as the end of the expression, so it will actually attempt to resolve the expression:

      ${some_table[${random_index}

This will result in an error and treat the remaining "`]}`" as just part of the rest of the string.


### Reference Expressions

Reference expressions deal with references to other tables included using the [`#!include` directive](#include-directive). The result of a reference expression is always the value of a *single* field from a randomly selected row in the referenced table. By default, this field is the leftmost column of the referenced table, but this behavior can be changed using indexing.

For the following examples, let's assume we have included a file like so: `#!include(other.csv)`. This means we can reference this table using the default name "`other`".

#### Default Reference Expression

> usage: `${other}`

Rolls for a random row from `other.csv` and replaces with the value in the leftmost field.

#### Indexed Reference Expression

> usage: `${other[SomeField]}`

Rolls for a random row from `other.csv` and replaces with the value of the field named `SomeField`. This allows indexing to specific fields within the row.

#### Previous Reference Expression

> usage: `${~}`

Replace with the value in the leftmost field of the row from the previous reference expression, meaning the result of this expression will always be from the exact same row as that of the previous expression.

Because this expression depends on the results of a prevous expression, it will cause an error if it is the first in a string. It is also important to understand the [resolution order](#resolution-order) of expressions when using this.

This kind of reference expression is most useful when combined with indexing to use multiple parts of the same row in a string, like so:

> usage: `The first field is ${other}, and some field of the same row is ${~[SomeField]}`

### Dice-Arithmetic Expressions

Dice-arithmetic expressions are for evaluating simple arithmetic and for generating random integers for use in that arithmetic. Any replacement expression will be treated as a dice-arithmetic expression by the resolver if the first character inside of the braces is any of these characters: `+-012345679(`.

It is important to note that *all* dice operations will be evaluated *before* any arithmetic operations.

Although dice-arithmetic expressions are resolved as one replacement expression, dice operations and arithmetic operations happen in separate steps and so their syntax should be discussed separately.

#### Dice Operations

> usage: `${XdY}`

Chooses `X` random numbers between 1 and `Y`, and replaces with the sum of all these numbers. For example, `${2d6}` will choose 2 random numbers between 1 and 6, and be replaced by the sum of those two numbers. The `${1d100}` will give a random number between 1 and 100.

All dice expressions are always resolved before any arithmetic expressions.

#### Arithmetic Operations

> usage: `${-(1 + 2 - 3 * 4 / 5 // 6 ** 7 % 8)}`

Resolves the contained arithmetic and replaces with the result. Supports the following arithmetic operations:

| Operation          | Example            |
| ------------------ | ------------------ |
| Addition           | `1 + 2 = 3`        |
| Subtraction        | `2 - 3 = -1`       |
| Multiplication     | `3 * 4 = 12`       |
| Division           | `30 / 8 = 3.75`    |
| Floor Division     | `30 // 8 = 3`      |
| Modulo (Remainder) | `9 % 4 = 1`        |
| Powers             | `2 ** 3 = 8`       |
| Parentheses        | `(4 + 5) * 6 = 54` |
| Negation           | `-(6 + 7) = -13`   |

## Table Style Guide

For most use cases, a consistent style is probably not strictly necessary. However, one practicality to consider is the placement of directives. For table readability, it is best to place all directives together at the very top or the very bottom of the file, but there are still some things to take into consideration when choosing between these two options.

Typical programming convention would place all include directives at the top, and this is slightly more convenient when editing CSV files. However, one of the advantages of using CSV files is the interoperability and portability of the format, including the possibility of using third-party tools to assist in editing and processing your tables.

Many third-party tools used to edit or process CSV files assume that if there is a header line, then it will always be the first line of the file. Because of this, it is likely that directives placed at the top of the file will cause more issues with third-party tools than they would if placed at the bottom. This could be something to consider if you plan on using other tools when building or using your library.

Speaking from personal experience of using `roll-table` while developing it, I haven't run into many issues caused by this, but I also only use Excel or OpenOffice Calc to edit my randomization tables.

### The Author's Opinion

This is just generally the style I follow while working on my tables, and most of the examples and test tables in this repo reflect that.

- Directives at the top
- Use `snake_case` when naming directories, CSV files, and include aliases
- Use `PascalCase` for the fieldnames in the header line to make them stand out a bit visually
