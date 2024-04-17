---
default_highlighter: oils-sh
---

JSON in Oils
===========

[JSON](https://www.json.org/) is used by both web services and command line
tools, so a modern Unix shell needs to support it.

Oils has a `json` builtin which you can use from bot OSH and YSH.

It also has a parallel `json8` builtin with the same uage.  See [J8
Notation](j8-notation.html) for details on the encoding.

<div id="toc">
</div>

The `json` **builtin** has `read` and `write` subcommands, which convert
between serialized data languages and in-memory data structures.

YSH data structures are like those in Python and JavaScript, so this
correspondence is natural.

## `json read` parses from `stdin`

Usage:

    json  read (PLACE?)
    json8 read (PLACE?)

Examples:

    $ cat stats.json
    {"count": 42}

    # Read from a file.  By default, the variable _reply is written.
    $ json read < stats.json

    # Use = to pretty print an expression
    $ = _reply
    (Dict)   {'count': 42}

Specify a place to put the data:

    $ json read (&myvar) < stats.json

    $ = myvar
    (Dict)   {'count': 42}

Use it in a pipeline:

    # 'json read' is valid at the end of a pipeline (because YSH implements
    # shopt -s lastpipe)
    $ echo '{"count": 42}' | json read (&myvar)

Failure with invalid input data:

    $ echo '[ "incomplete"' | json read (&myvar) < invalid.json
    [ "incomplete"
     ^
    json read: premature EOF

    $ echo $?
    1

## `json write` prints to `stdout`

Usage:

    json write (EXPR, space=2)
    
    EXPR is an expression that evaluates to a serializable object.

    space is the number of spaces that object and array entries are indented
    by.  If it's 0 or less, then no newlines or spaces are printed.

Examples:

    $ var d = {name: "bob", age: 42}  # create Dict

    $ json write (d)  # print as JSON, with 2 space indent
    {
      "name": "bob",
      "count": 42
    }

    $ json write (d, space=0)  # no indent at all
    {"name":"bob","count":42}

### `write` builtin

TODO

    write --j8 hello there
    write --json hello there  # unicode replacement char

## Filter Data Structures with YSH Expressions

Once your data is deserialized, you can use YSH expression to operate on it.

    $ echo '{"counts": [42, 99]}' | json read (&d)

    $ = d['counts']
    (List)   [42, 99]

    $ = d['counts'][1]
    (Int)    99

    # d->counts is a synonym for d["counts"]
    $ json write (d->counts)
    [
      42,
      99
    ]

Note: It may more efficient to filter large data structures with tools like
`jq` first.

## Other Data Structures Can Be Printed as JSON

YSH arrays and shell arrays both serialize to a list of strings:

    $ declare sharray=( foo.txt *.py )
    $ json write (sharray)
    [  
       "foo.txt",
       "one.py",
       "two.py"
    ]

    $ var oilarray = :| foo.txt *.py |
    $ json write (oilarray)
    [  
       "foo.txt",
       "one.py",
       "two.py"
    ]

Bash-style associative arrays are printed like `Dict[Str, Str]`:

    $ declare -A assoc=(["key"]=value)
    $ json write (assoc)
    {
      "key": "value"
    }

