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

### Function Sub Isn't Sllowed Double Quoted Strings

You can do

    echo $f(x)

but not

    echo "_ $f(x) _"   # means the variable $f and then literals '(x)' !

Instead you have to use an expression sub:

    echo "_ $[f(x)] _"

You can also factor it out:

    var s = f(x)
    echo "_ $s _"

To disambiguate the cases, use explicit braces:

    echo "_ ${f}(x) _"  # variable f
    echo "_ $[f(x)] _"  # function call f

## Related 

- The doc on [compatibility quirks](quirks.html) relates to the OSH language.

