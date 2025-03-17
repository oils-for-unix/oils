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

## no-quotes

### nq-assert

Use the syntax of the [test][] builtin to assert a condition is true.

    nq-assert 99 = "$status"
    nq-assert "$status" -lt 2


[test]: chap-builtin-cmd.html#test

### nq-run

Run a command and "return" its status with nameref variables.

    test-foo() {
      local status

      nq-run status \
        false
      nq-assert 1 = "$status"
    }

### nq-capture

Run a command and return its status and stdout.

### nq-capture-2

Run a command and return its status and stderr.

### nq-redir

Run a command and return its status and a file with its stdout, so you can diff
it.

### nq-redir-2

Run a command and return its status and a file with its stderr, so you can diff
it.

## task-five

### task-five

Dispatch to shell functions, and provide BYO test enumeration.

OSH:

    task-five "$@"

YSH:

    task-five @ARGV

## math

### abs()

Compute the absolute (positive) value of a number (float or int).

    = abs(-1)  # => 1
    = abs(0)   # => 0
    = abs(1)   # => 1

Note, you will need to `source $LIB_YSH/math.ysh` to use this function.

### max()

Compute the maximum of 2 or more values.

`max` takes two different signatures:

  1. `max(a, b)` to return the maximum of `a`, `b`
  2. `max(list)` to return the greatest item in the `list`

For example:

      = max(1, 2)  # => 2
      = max([1, 2, 3])  # => 3

Note, you will need to `source $LIB_YSH/math.ysh` to use this function.

### min()

Compute the minimum of 2 or more values.

`min` takes two different signatures:

  1. `min(a, b)` to return the minimum of `a`, `b`
  2. `min(list)` to return the least item in the `list`

For example:

    = min(2, 3)  # => 2
    = max([1, 2, 3])  # => 1

Note, you will need to `source $LIB_YSH/math.ysh` to use this function.

### round()

TODO

### sum()

Computes the sum of all elements in the list.

Returns 0 for an empty list.

    = sum([])  # => 0
    = sum([0])  # => 0
    = sum([1, 2, 3])  # => 6

Note, you will need to `source $LIB_YSH/list.ysh` to use this function.


## list

### all()

Returns true if all values in the list are truthy (`x` is truthy if `Bool(x)`
returns true).

If the list is empty, return true.

    = any([])  # => true
    = any([true, true])  # => true
    = any([false, true])  # => false
    = any(["foo", true, true])  # => true

Note, you will need to `source $LIB_YSH/list.ysh` to use this function.

### any()

Returns true if any value in the list is truthy (`x` is truthy if `Bool(x)`
returns true).

If the list is empty, return false.

    = any([])  # => false
    = any([true, false])  # => true
    = any([false, false])  # => false
    = any([false, "foo", false])  # => true

Note, you will need to `source $LIB_YSH/list.ysh` to use this function.

### repeat()

Repeat a string or a list:

    = repeat('foo', 3)           # => 'foofoofoo'
    = repeat(['foo', 'bar'], 2)  # => ['foo', 'bar', 'foo', 'bar']

Negative repetitions are equivalent to zero:

    = repeat('foo', -5)           # => ''
    = repeat(['foo', 'bar'], -5)  # => []

Note that the `repeat()` function is modeled after these Python expressions:

    >>> 'a' * 3
    'aaa'
    >>> ['a'] * 3
    ['a', 'a', 'a']

## yblocks

Helpers to assert the status and output of commands.

### yb-capture

Capture the status and stdout of a command block:

    yb-capture (&r) {
      echo hi
    }
    assert [0 === r.status]
    assert [u'hi\n' === r.stdout]

### yb-capture-2

Capture the status and stderr of a command block:

    yb-capture-2 (&r) {
      echo hi >& 2
    }
    assert [0 === r.status]
    assert [u'hi\n' === r.stderr]

## args

YSH includes a command-line argument parsing utility called `parseArgs`. This
is intended to be used for command-line interfaces to YSH programs.

To use it, first import `args.ysh`:

    source $LIB_YSH/args.ysh

Then, create an argument parser **spec**ification:

    parser (&spec) {
      flag -v --verbose (help="Verbosely")  # default is Bool, false

      flag -P --max-procs (Int, default=-1, help='''
        Run at most P processes at a time
        ''')

      flag -i --invert (Bool, default=true, help='''
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
      flag -N --count (Int)
    }

Calling `parseArgs` with `ARGV = :| -N 5 |` or `ARGV = :| --count 5 |` will
store the integer `5` under `args.count`. If the user passes in a non-integer
value like `ARGV = :| --count abc |`, `parseArgs` will raise an error.

The supported flag types are `Bool`, `Int`, `List[Int]`, `Float`, `List[Float]`,
`Str`, and `List[Str]`.

Flags with a `List` type may be provided multiple times. For example, if you
wanted to accept a list of strings:

    parser (&spec) {
        flag -f --file (List[Str])
    }

Calling `parseArgs` with `ARGV = :| -f a --file b -f c |` will store the value
`['a', 'b', 'c']` under `args.file`.

Default values for an argument can be set with the `default` named argument.

    parser (&spec) {
      flag -N --count (Int, default=2)

      # Boolean flags can be given default values too
      flag -O --optimize (Bool, default=true)
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

## binascii

<!--

2025-02: Added because terminals like Jetbrains/Warp shell out to 'od', to fit
data in OSC escapes.  In OSH you should be able to do it within the process.

And these should be FAST - that's a good test of any algorithm.

I also wonder about quoteHtml(), unquoteHtml(), quoteSh(), unquoteSh, etc. -
those are also translations.  Do we need a string.translate API?

https://docs.python.org/3/library/base64.html

https://github.com/python/cpython/blob/3.13/Lib/base64.py

https://docs.python.org/2.7/library/binascii.html#module-binascii

I chose the name "binascii" because base64.toBase16 is a little weird

Could be "codec" too?

-->

### toBase16

TODO

### fromBase16

TODO

### toBase64

TODO

### fromBase64

TODO
