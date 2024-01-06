---
default_highlighter: oils-sh
---

YSH Language Warts
==================

This documents describes parts of the YSH language that may be surprising.

All languages have warts, but most of them don't document them for you!  Even a
nice language like Python has surprising cases like `42,` and `f(x),` being a
1-tuple (because of the trailing comma).

The goal of YSH is to remove the many warts of shell, documented at [Shell
WTFs][wtfs].  Nonetheless it has some of its own.

[wtfs]: https://github.com/oilshell/oil/wiki/Shell-WTFs

<div id="toc">
</div>

## For Bash Compatibility

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
YSH.

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

## Related 

- The doc on [compatibility quirks](quirks.html) relates to the OSH language.

