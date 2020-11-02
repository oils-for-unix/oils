---
default_highlighter: oil-sh
---

Shell Language Idioms
=====================

This is like [Oil Language Idioms](idioms.html), but the advice also applies to
shells other than Oil.

<div id="toc">
</div>

## Use Statically Parsed Language Constructs

Static parsing is one of the [syntactic concepts](syntactic-concepts.html).  It
leads to better error messages, earlier error messages, and lets tools
understand your code.

### Prefer Shell Functions to Aliases

Functions subsume all the common uses of alias, and can be parsed statically.

No:

    alias ll='ls -l'    

Yes:

    ll() {         # Shell Style
      ls -l "$@"
    }

    proc ll {      # Oil Style
      ls -l @ARGV
    }

### Prefer `$'\n'` to `echo -e`

No:

    echo -e '\n'   # arg to -e is dynamically parsed

Yes:

    echo $'\n'     # statically parsed


### `test` Should Only Have 2 or 3 Arguments

In POSIX, the `test` builtin has a lot of unnecessary flexibility, which leads
to bugs.

See [Problems With the test Builtin: What Does -a
Mean?](//www.oilshell.org/blog/2017/08/31.html)

No:

    test ! -d /tmp
    test -d /tmp -a -d /tmp/foo

Yes:

    ! test -d /tmp
    test -d /tmp && test -d /tmp/foo

The [simple_test_builtin]($oil-help) option enforces that `test` receives 3 or
fewer arguments.

## Style

### Prefer `test` to `[`

Idiomatic Oil code doesn't use "puns".

No:

    [ -d /tmp ]

Yes:

    test -d /tmp

