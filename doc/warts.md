---
default_highlighter: oil-sh
---

Oil Language Warts
==================

This documents describes parts of the Oil language that may be surprising.

All languages have warts, but most of them don't document them for you!  Even a
nice language like Python has surprising cases like `42,` and `f(x),` being a
1-tuple (because of the trailing comma).

Oil's goal is to remove the many warts of shell, documented at [Shell
WTFs][wtfs].  Nonetheless it has some of its own.

[wtfs]: https://github.com/oilshell/oil/wiki/Shell-WTFs

<div id="toc">
</div>

## For Bash Compatibility

### C-Escaped Strings

The `$'line\n'` syntax is confusing because of the `$` character.

- C-escaped strings don't allow `${var}` interpolation.
- It has nothing to do with substitution like `${var}` or `$(hostname)`.

It's also not consistent with raw strings like `r'foo'`, while `c'foo'` would
be.

If we were starting from scratch, I would have chosen a different prefix, but
it isn't worth the breakage and complexity.  All string literals exist in both
command and expression mode, which is tricky to implement.

<!-- TODO: remove in favor of j"" -->

### Two Left Parens Should be Separated By Space

No:

    if ((x + 1) < n) {  # note ((
      echo 'less'
    }

Yes:

    if ( (x + 1) < n) {  # add a space
      echo 'less'
    }

This is because the `((` token is for bash arithmetic, which is disallowed in
Oil.

### Two Different Syntaxes For `Block` and `Expr` Literals

Blocks look different in command vs expression mode:

    cd /tmp {                   # command mode { }
      echo $PWD
    }
    var myblock = ^(echo $PWD)  # expression mode, lazy ^( )

So do expressions:

    myproc | where (age > 10)   # command mode, lazy ( )
    var myval = age > 10        # expression mode
    var myexpr = ^[age > 10]    # expression mode, lazy ^[ ]

It would have been nicer if they were consistent, but shell is already
inconsistent with `$(echo hi)` and `{ echo hi; }`.

There is consistency in other directions:

- `^(echo $PWD)` is consistent with shell's eagerly evaluated `$(echo $PWD)`.
- `^[42 + f(x)]` is consistent with expression sub `$[42 + f(x)]`.

Most users won't see these literal forms very much.  They're more useful for
testing and frameworks rather than simple scripts/applications.

## In `read :x`, The Colon is a "Pseudo-Sigil"

<!-- TODO: remove in favor of value.Place -->

Sigils like `$` and `@` are [statically
parsed](https://www.oilshell.org/blog/2019/02/07.html), but the optional `:` is
dynamically parsed by every builtin that supports it.

This is a minor inconsistency, but I like having a symbol for a variable to be
mutated.

## Related 

- The doc on [compatibility quirks](quirks.html) relates to the OSH language.

