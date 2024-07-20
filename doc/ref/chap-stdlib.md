---
title: Builtin Commands (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash; Chapter **Standard Library**

</div>

This chapter in the [Oils Reference](index.html) describes the standard library
for OSH and YSH.

(These functions are implemented in OSH or YSH, not C++ or Python.)

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

## two

These functions are in `two.sh`

    source $OSH_LIB/two.sh

### log

Write a message to stderr:

    log "hi $x"
    log '---'

### die

Write an error message with the script name, and exit with status 1.

    die 'Expected a number'

## Args Parser

YSH includes a command-line argument parsing utility called `parseArgs`. This
is intended to be used for command-line interfaces to YSH programs.

To use it, first import `args.ysh`:

    source --builtin args.ysh

Then, create an argument parser **spec**ification:

    parser (&spec) {
      flag -v --verbose (help="Verbosely")  # default is Bool, false

      flag -P --max-procs ('int', default=-1, help='''
        Run at most P processes at a time
        ''')

      flag -i --invert ('bool', default=true, help='''
        Long multiline
        Description
        ''')

      arg src (help='Source')
      arg dest (help='Dest')

      rest files
    }

Finally, parse `ARGV` (or any other array of strings) with:

    var args = parseArgs(spec, ARGV)

The returned `args` is a `Dict` containing key-value pairs with the parsed
values (or defaults) for each flag and argument. For example, given
`ARGV = :| mysrc -P 12 mydest a b c |`, `args` would be:

    {
        "verbose": false,
        "max-procs": 12,
        "invert": true,
        "src": "mysrc",
        "dest": "mydest",
        "files": ["a", "b", "c"]
    }

### parser

`parseArgs()` requires a parser specification to indicate how to parse the
`ARGV` array. This specification should be constructed using the `parser` proc.

    parser (&spec) {
      flag -f --my-flag
      arg myarg
      rest otherArgs
    }

In the above example, `parser` takes in a place `&spec`, which will store the
resulting specification and a block which is evaluated to build that
specification.

Inside of a `parser` block, you should call the following procs:

- `flag` to add `--flag` options
- `arg` to add positional arguments
- `rest` to capture remaining positional arguments into a list

`parser` will validate the parser specification for errors such as duplicate
flag or argument names.

    parser (&spec) {
      flag -n --name
      flag -n --name  # Duplicate!
    }

    # => raises "Duplicate flag/arg name 'name' in spec" (status = 3)

### flag

`flag` should be called within a `parser` block.

    parser (&spec) {
      flag -v --verbose
    }

The above example declares a flag "--verbose" and a short alias "-v".
`parseArgs()` will then store a boolean value under `args.verbose`:
- `true` if the flag was passed at least once
- `false` otherwise

Flags can also accept values. For example, if you wanted to accept an integer count:

    parser (&spec) {
      flag -N --count ('int')
    }

Calling `parseArgs` with `ARGV = :| -n 5 |` or `ARGV = :| --count 5 |` will
store the integer `5` under `args.count`. If the user passes in a non-integer
value like `ARGV = :| --count abc |`, `parseArgs` will raise an error.

Default values for an argument can be set with the `default` named argument.

    parser (&spec) {
      flag -N --count ('int', default=2)

      # Boolean flags can be given default values too
      flag -O --optimize ('bool', default=true)
    }

    var args = parseArgs(spec, :| -n 3 |)
    # => args.count = 2
    # => args.optimize = true

Each name passed to `flag` must be unique to that specific `parser`. Calling
`flag` with the same name twice will raise an error inside of `parser`.

<!-- TODO: how can we explicitly pass false to a boolean flag? -->
<!-- TODO: how about --no-XXXX variants of flags? -->

### arg

`arg` should be called within a `parser` block.

    parser (&spec) {
      arg query
      arg path
    }

The above example declares two positional arguments called "query" and "path".
`parseArgs()` will then store strings under `args.query` and `args.path`. Order
matters, so the first positional argument will be stored to `query` and the
second to `path`. If not enough positional arguments are passed, then
`parseArgs` will raise an error.

Similar to `flag`, each `arg` name must be unique. Calling `arg` with the same
name twice will cause `parser` to raise an error.

### rest

`rest` should be called within a `parser` block.

    parser (&spec) {
      arg query
      rest files
    }

Capture zero or more positional arguments not already captured by `arg`. So,
for `ARGV = :| hello file.txt message.txt README.md |`, we would have
`args.query = "file.txt"` and `args.files = ["file.txt", "message.txt",
"README.md"]`.

Without rest, passing extraneous arguments will raise an error in
`parseArgs()`.

`rest` can only be called _once_ within a `parser`. Calling it multiple times
will raise an error in `parser`.

### parseArgs()

Given a parser specification `spec` produced by `parser`, parse a list of
strings (usually `ARGV`.)

    var args = parseArgs(spec, ARGV)

The returned `args` is a dictionary mapping the names of each `arg`, `flag` and
`rest` to their captured values. (See the example at the [start of this
topic](#Args-Parser).)

`parseArgs` will raise an error if the `ARGV` is invalid per the parser
specification. For example, if it's missing a required positional argument:

    parser (&spec) {
      arg path
    }

    var args = parseArgs(spec, [])
    # => raises an error about the missing 'path' (status = 2)

<!--
TODO: Document chaining parsers / sub-commands
      - Either will allow parser nesting
      - Or can use `rest rest` and `parseArgs` again on `rest`
TODO: Document the help named argument. Punting while we do not generate help messages
-->
