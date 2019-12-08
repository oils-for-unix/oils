JSON in Oil
===========

[JSON](https://www.json.org/) is used by both web services and command line
tools, so a modern Unix shell needs support for it.

This page describes Oil's JSON support as of December 2019 ([version
0.7.pre8](/release/0.7.pre8)).  It will likely expand over time, depending on
[user feedback](https://github.com/oilshell/oil/wiki/Where-To-Send-Feedback).

(Note: the `help` builtin will provide shorter, reference-style documentation.)

<!-- cmark.py expands this -->
<div id="toc">
</div>

The `json` **builtin** has `read` and `write` subcommands, which convert
between text and data structures in memory.  Oil's data structures are like
those in Python and JavaScript, so this correspondence is natural.

## `json read` parses from `stdin`

Usage:

    json read FLAGS* VAR_NAME

    Flags:
      None for now, but there likely will be one to skip UTF-8 validation.

Examples:

    $ cat stats.json
    {"count": 42}

    # Read from a file.  myvar is created in local scope.
    $ json read :myvar < stats.json

    # Use = to pretty print an expression
    $ = myvar   
    (Dict)   {'count': 42}

    # 'json read' is valid at the end of a pipeline (because Oil implements
    # shopt -s lastpipe)
    echo '{"count": 42}' | json read :myvar

    # Failure with invalid input data
    $ echo '[ "incomplete"' | json read :myvar < invalid.json
    [ "incomplete"
     ^
    json read: premature EOF

    $ echo $?
    1

Notes:

- Variable names may be prefixed with the **optional** "sigil" `:`.
- `json read` is consistent with shell's `read` builtin, which reads a *line*
  from a file and splits it.
- Only one variable name can be passed.

## `json write` prints to `stdout`

Usage:

    json write FLAGS* VAR_NAME+
    
    Flags:
      -indent=2     Indentation size
      -pretty=true  Whether to add newlines for readability

Examples:

```
# Create a Dict.  As in JavaScript, keys don't require quotes.
$ var d = {name: "bob", age: 42}

# Print the Dict as JSON.  By default, newlines are added for readability, with
# 2 space indentation.
$ json write :d
{
  "name": "bob",
  "count": 42
}

$ json write -indent 4 :d
{
    "name": "bob",
    "count": 42
}

$ json write -pretty=F :d
{"name": "bob", "count": 42}
```

Notes:

- `-indent` is ignored if `-pretty` is false.
- The `json` builtin is part of the Oil language, so it uses Oil's **flag
  syntax**, which is based on Go's.  In particular, boolean flags are written
  `-pretty=F` rather than `-pretty F`, but you can write `-indent=4` or
  `-indent 4`.

## Other Data Structures Can Be Printed as JSON

Oil arrays and shell arrays both serialize to a list of strings:

    $ declare sharray=( foo.txt *.py )
    $ json write :sharray
    [  
       "foo.txt",
       "one.py",
       "two.py"
    ]

    $ var oilarray = @( foo.txt *.py )
    $ json write :oilarray
    [  
       "foo.txt",
       "one.py",
       "two.py"
    ]

Bash-style associative arrays are printed like `Dict[Str, Str]`:

    $ declare -A assoc=(["key"]=value)
    $ json write :assoc
    {
      "key": "value"
    }

## Credits

Under the hood, Oil uses [yajl](https://lloyd.github.io/yajl/) and a fork of
the [py-yajl](https://github.com/oilshell/py-yajl) binding.
