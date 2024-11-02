---
default_highlighter: oils-sh
---

What Breaks When You Upgrade to YSH
===================================

Only a few things break when you put this at the top of a shell script:

    shopt --set ysh:upgrade

This doc enumerates and explains them.

<div id="toc">
</div>

## Reasons for Upgrading

First, let's emphasize the **good** things that happen when you upgrade:

- You can write `if (x > 0)` instead of `if [ "$x" -gt 0 ]`.
- You can pass blocks to commands, like `cd /tmp { echo $PWD }`
- [Simple Word Evaluation](simple-word-eval.html): You can write `$var` instead
  of `"$var"`, and splice arrays with `@myarray`.
- [Reliable Error Handling](error-handling.html) becomes the default.
- ... and more

You can also use `bin/osh` indefinitely, in which case you don't need to read
this doc.  [OSH]($xref:osh-language) is a highly compatible Unix shell.

## Syntax Changes

Now onto the breakages.  Most of them are **unlikely**, but worth noting.

### `if ( )` and `while ( )` take expressions, not subshell commands

Code like `if ( ls /tmp )` is valid shell, but it's almost always a misuse of
the language.  Parentheses mean **subshell**, not grouping as in C or Python.

In YSH:

- Use `if (x > 0)` for true/false expressions
- Use the `forkwait` builtin for subshells, which are uncommon.  (It's like
  invoking the `fork` builtin, then the `wait` builtin.)

No:

    ( cd /tmp; rm *.sh )

Yes:

    forkwait {
      cd /tmp
      rm *.sh
    }

Better:

    cd /tmp {  # no process created
      rm *.sh
    }
    echo $PWD  # restored


(Option `parse_paren` is part of group `ysh:upgrade`.)

### `@()` is spliced command sub, not extended glob 

YSH doesn't have implicit word splitting, so we want `@(seq 3)` to be
consistent with `$(hostname)`.  They're related in the same way that `@myarray`
and `$mystr` are.

This means that `@()` is no longer extended glob, and `,()` is an alias.

No:

    echo @(*.cc|*.h)

Use this YSH alias instead:

    echo ,(*.cc|*.h)

(Option `parse_at` is part of group `ysh:upgrade`.)

### `r'c:\Users\'` is a raw string, not joined strings

The meaning of `\` within string literals can be confusing, so YSH
distinguishes them like this:

- `$'foo\n'` 
  - The `$` prefix means that C-style backslash escapes are respected.
- `r'c:\Users\'` 
  - The `r` prefix means the backslashes are literal.
  - In shell this is written `'c:\Users\'`.  YSH accepts this in command mode
    for compatibility, but not expression mode.

The prefix **changes** the meaning of commands like:

    echo r'foo'
    # => foo in YSH
    # => rfoo in shell, because of implicit joining

Instead, write `'rfoo'` if that's what you mean.

(Option `parse_raw_string` is part of group `ysh:upgrade`.)

### globs can't start with `[`

In a command, the `[` character starts a lazy arg list:

    assert [42 === x]

In shell, `[` is part of the glob syntax:

    echo [ch]  # extremely rare pattern matching c or h

This is more common, and still works:

    echo *.[ch]

You can still express the former by explicitly invoking `glob('[ch]')`.


(Option `parse_bracket` is part of group `ysh:upgrade`.)

## Unsupported

### Extended Globs in Word Evaluation

Like regular globs, the extended glob syntax is used in two ways:

1. Pattern matching 
   - `case` 
   - Bash boolean expressions like `[[ x == !(*.cc|*.h) ]]`
2. Word Evaluation
   - commands like `cp !(*.cc|*.h) /tmp`
   - arrays like `local -a myarray=( !(*.cc|*.h) )`
   - Shell-style `for` loops

Extended globs are **not** supported in [Simple Word
Evaluation](simple-word-eval.html), so you can't use them in the second way
after upgrading.

You may want to use the `find` command or [Egg expressions](eggex.html)
instead.

(Option `simple_word_eval` is part of group `ysh:upgrade`.)

## More Quotes May Be Needed

### With `ysh:upgrade` Options

Option `parse_at`.  In YSH, `@` is used to splice arrays.  To pass a string
`@foo` to a command, quote it like `'@foo'`.

Option `parse_brace`.  Braces after commands start block arguments.  To change
to a directory named `{`, quote it like `cd '{'`.

Option `parse_equals`.  A statement like `x = 42` is a "bare assignment" or
attribute.  To pass `=` to a command `x`, quote it like `x '='`.

### Unconditionally

- To avoid confusion with YSH's `=` operator, a word like `=x` can't be the first word in a command.
  To invoke such commands, quote them like `'=x'`.
- YSH has new keywords like `proc`, `const`, `var`, and `setvar`.  To use them
  as command names, quote them like `'proc'`.

There is very little reason to use commands like `'=x'` and `'proc'`, so you
will likely never run into this!

## Summary

This concludes the list of features that's broken when you upgrade from OSH to
YSH.  We tried to keep this list as small as possible.

There are other features that are **discouraged**, like `$(( x + 1 ))`, `(( i++
))`, `[[ $s =~ $pat ]]`, and `${s%%prefix}`.  These have better alternatives in
the YSH expression language, but they can still be used.  See [YSH vs. Shell
Idioms](idioms.html).

Also related: [Known Differences Between OSH and Other
Shells](known-differences.html).

## Appendix

Here are some notable **non-breaking** changes.

### Shell Functions vs. Procs

Procs have truly local variables like Python and JavaScript.  There's no
[dynamic scope]($xref:dynamic-scope) rule, as with shell functions.

This is something to be aware of, but isn't technically a breakage because
shell functions still work the same way in YSH.

### $EDITOR vs. ENV.EDITOR 

In YSH, env vars live in the [ENV][] dict.  So instead of `$EDITOR`, you should
use `$[ENV.EDITOR]`.

But doesn't break when you `shopt --set ysh:upgrade`, only when you use
`bin/ysh`.

[ENV]: ref/chap-special-var.html#ENV

### Acknowledgments

Thank you to `ca2013` for reviewing this doc.

