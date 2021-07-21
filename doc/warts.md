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

### Function Sub Isn't Allowed in Double Quoted Strings

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

### Two Different Syntaxes For `Block` and `ArgList` Literals

Blocks look different in command vs expression mode:

    cd /tmp {                   # command mode { }
      echo $PWD
    }
    var myblock = ^(echo $PWD)  # expression mode ^( )

So do lazily evaluated arg lists (not yet implemented):

    myproc | filter [age > 10]  # command mode [ ]
    var myexpr = ^{age > 10}    # expression mode ^{ }

It would have been nicer if they were consistent, but:

- `^(echo $PWD)` is consistent with `$(echo $PWD)` (eagerly evaluated)
- Expression literals `^[42 + f(x)]` are consistent with `$[42 + f(x)]`
  (eagerly evaluated).  So the `age > 10` has to use a different sigil pair,
  which is `^{age > 10}`.
- Most users won't see these literal forms very much.  They're more useful for
  testing and frameworks rather than simple scripts/applications.

## In `read :x`, The Colon is a "Pseudo-Sigil"

Sigils like `$` and `@` are [statically
parsed](https://www.oilshell.org/blog/2019/02/07.html), but the optional `:` is
dynamically parsed by every builtin that supports it.

This is a minor inconsistency, but I like having a symbol for a variable to be
mutated.

## Related 

- The doc on [compatibility quirks](quirks.html) relates to the OSH language.

