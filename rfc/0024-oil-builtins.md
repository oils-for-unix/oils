Oil Builtins
------------

We're upgrading builtins.

### Compatible Enhancements


### Related Shell Options

#### `shopt -s longopts`

Builtins take long flags, e.g.

    read -timeout 1.0
    read -timeout=1.0

    read --timeout 1.0
    read --timeout=1.0

So flags can't be smooshed together:

    set -eu                    # NO
    set -e -u                  # YES
    set -o errexit -o nounset  # better

### Changed by Options


#### `shopt -s oil-echo`

- echo accepts -- for consistency.  We want `mybuiltin @flags -- @args` to be
  valid no matter what.
- It accepts `-sep` and `-end` flags like Python's `print`.
  - The default separator is a NEWLINE.  This is more useful and less
    confusing.
  - The default end is a NEWLINE, like Python.
- `echo -n` is an alias for `echo -end ''`
- `echo -e` is disallowed in favor of C strings:
  - `echo $'\n'` (unfortunate wart, but statically parsed and has to exist)
  - `var s=c'\n'; echo $s`

Examples:

    echo -sep ' ' -- @words  # instead of the default $'\n'

    echo -end $'\r\n' -- @words  # plausible use case?

A raw `write` can be an alias for this:

    echo -sep '' -end '' -- @ARGV


#### `shopt -s oil-eval-builtin`

The args aren't joined.  Zero args or More than one arg is an error

Also accepts -- (but there are no flags).

- Or should it allow parse time flags?
  - eval -O oil-parse-at ?
    - or instead of -O and +O, should it be -s and -u ?

#### `shopt -s oil-trap`

It takes a function name,  not a code string

This is better for parse time options (`shopt -s oil-parse-*`).  The parsing is
dictated by the surrounding file.

#### `shopt -s oil-test-builtin`

test -file


### Builtins Upgraded With a Block

#### cd, shopt, env

- cd { ... } subsumes pushd and popd

- we're not changing `set`, only `shopt`

- should `shopt` unify `set` and `shopt`?
  - the `-o` flag is ugly

- `env` is backward-compatible with /usr/bin/env
  - an `env` block is preferred over export
  - it also is required for `shopt -s parse-equals`, so
    that `PYTHONPATH=. ./foo.py` isn't parsed as an assignment.
    - it's now `env PYTHONPATH=. ./foo.py`

#### fork, wait

- fork is new.  wait is old.

#### each

This is "xargs v2", and it takes both flags and a block.

### Other Builtins

#### repr

For debugging variable representations.

Should there also be a 'trace' builtin?  To show line numbers?  Better than
xtrace.  Or maybe just CALL it `xtrace` or `xt`.

Or maybe it should be

    repr -v x y  # -v flag shows soure location and indents with
                 # call stack maybe?

#### push

To append to an array.  The name is borrowed from Perl/JavaScript.

#### log, die (polyfill)

And maybe 'write'?  Although the sep can't be ''.

#### dirname, basename (optimizations)

#### use (modules with namespaces)

See 0026-use-namespaces.md.


### Deprecated

- **All assignment builtins** are deprecated, except `export`.
- `export` becomes a regular builtin that only takes names, not an assignment
  builtin with statically and dynamically parsed `name=val`.
  - An `env` block is generally better.
  - And you can use `declare -x`.

Maybe there should be `shopt -u old-builtins` (make them invisible, default is
visible).

- `pushd`, `popd` -- use `cd ~/src { ... }` instead
  - and `dirs`

- alias, unalias -- not sure how we would deprecate
  - bash already has `shopt -s expand_alias`

- `source` in favor of use?
- `printf` in favor of statically parsed `${x %02d}`

- `getopts` in favor of something nicer, `optspec` or `argspec` based on oil
  blocks?
  - or just `opts` or `args`?

Speculative:

- `command` and `builtin` could be subsumed by some more general $PATH
  mechanism?


### Other Ideas

`prefix` builtin?

    prefix git -C . {
      add foo.txt
      rm foo.txt
    }


Or maybe just `command`?  Not `builtin`?

    command git -C . {
      add foo.txt
      rm foo.txt
    }

`command` does find builtins though, e.g. `command echo ls` works.

That would conflict with 

    command cd {
      /
      d
    }

