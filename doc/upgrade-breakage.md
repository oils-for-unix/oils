---
default_highlighter: oil-sh
---

What Breaks When You Upgrade to Oil
===================================

Only a few things break when you put this at the top of a shell script:

    shopt --set oil:upgrade

This doc enumerates and explains them.

On the other hand, there are many good things that happen:

- You can write `if (x > 0)` instead of `if [ "$x" -gt 0 ]`.
- You can pass blocks to commands, like `cd /tmp { echo $PWD }`
- [Simple Word Evaluation](simple-word-eval.html): You can write `$var` instead
  of `"$var"`, and splice arrays with `@myarray`.
- [Reliable Error Handling](error-handling.html) becomes the default.
- ... and more

You can also use `bin/osh` indefinitely, which means you **don't** have to read
this doc.

<div id="toc">
</div>

## Change in Syntax

You're unlikely to hit these problems, but they're worth noting.

### `if ( )` and `while ( )` take expressions, not subshells

Code like `if ( ls )` is valid shell, but it's almost always a
**misuse** of the language.  Parentheses mean **subshell**, not grouping as in
C or Python.

In Oil:

- `if (x > 0)` is used for expressions
- the `forkwait` builtin is for subshells, which are uncommon.  
  - Think of it as a sequence of the `fork` builtin (replaces `&`) and the
    `wait` builtin.

No:

    ( not_mutated=foo )
    echo $not_changed

Yes:

    forkwait {
      setvar not_changed = 'foo'
    }
    echo $not_changed

Note that the idiom of running commands in a different dir no longer requires
a subshell:

No:

    ( cd /tmp; echo $PWD )
    echo $PWD  # still the original value

Yes:

    cd /tmp {
      echo $PWD 
    }
    echo $PWD  # restored


(Option `parse_paren` is part of group `oil:upgrade`.)

### `@()` is spliced command sub, not extended glob 

Oil doesn't have implicit word splitting, so we want `@(seq 3)` to be
consistent with `$(hostname)`.  They're related in the same way that `@myarray`
and `$mystr` are.

This means that `@()` is no longer extended glob, and `,()` is an alias.

No:

    echo @(*.cc|*.h)

Use this Oil alias instead:

    echo ,(*.cc|*.h)

(Option `parse_at` is part of group `oil:upgrade`.)

### `r'c:\Users\'` is a raw string `'c:\Users\'`

The meaning of `\` within string literals can be confusing, so Oil
distinguishes them like this:

- `$'foo\n'` 
  - The `$` prefix means that C-style backslash escapes are respected.
- `r'c:\Users\'` 
  - The `r` prefix means the backslashes are literal.
  - In shell this is written `'c:\Users\'`.  Oil accepts this in command mode
    for compatibility, but not expression mode.

The prefix **changes** the meaning of commands like:

    echo r'foo'
    # => foo in Oil
    # => rfoo in shell, because of implicit joining

Instead, write `'rfoo'` if that's what you mean.

(Option `parse_raw_string` is part of group `oil:upgrade`.)

## Deprecated

### Extended Globs in Commands and Arrays

Like regular globs, the extended glob syntax is used in two ways:

1. Pattern matching 
   - `case` 
   - Bash boolean expressions like `[[ x == !(*.cc|*.h) ]]`
2. Word Evaluation
   - commands like `cp !(*.cc|*.h) /tmp`
   - arrays like `local -a myarray=( !(*.cc|*.h) )`
   - Shell-style `for` loops

Extended globs are **not** implemented in [Simple Word
Evaluation](simple-word-eval.html), so you can't use them in the second way.

Instead of extended globs, use the `find` command or [Egg
expressions](eggex.html).

(Option `simple_word_eval` is part of group `oil:upgrade`.)

## More Quotes May Be Needed

### Unconditionally Changed

- To avoid confusion with Oil's `=` operator, a word like `=x` can't be the first word in a command.
  To invoke such commands, quote them like `'=x'`.
- Oil has new keywords like `proc`, `const`, `var`, and `setvar`.  To use them
  as command names, quote them like `'proc'`.

There is very little reason to use commands like `'=x` and `proc`, so you will
likely never run into this!

### Gated by Options

Option `parse_at`.  In Oil, `@` is used to splice arrays.  To pass a string
`@foo` to a command, quote it like `'@foo'`.

Option `parse_brace`.  Braces after commands start block arguments.  To change
to a directory named `{`, quote it like `cd '{'`.

Option `parse_equals`.  A statement like `x = 42` is a "bare assignment" or
attribute.  To pass `=` to a command `x`, quote it like `x '='`.

## Summary

This concludes the list of features that's broken when you upgrade from OSH to
Oil.  We tried to keep this list as small as possible.

There are other features that are **discouraged**, like `$(( x + 1 ))`, `(( i++
))`, `[[ $s =~ $pat ]]`, and `${s%%prefix}`.  These have better alternatives in
the Oil expression language, but they can still be used.  See [Oil vs. Shell
Idioms](idioms.html).

## Related

- [Known Differences Between OSH and Other Shells](known-differences.html)


