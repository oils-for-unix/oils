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
- [Reliable Error Handling](error-handling.html) becomes the default.
- [Simple Word Evaluation](simple-word-eval.html): You can write `$var` instead
  of `"$var"`, and splice arrays with `@myarray`.
- ... and more

You can also use `bin/osh` indefinitely, which means you **don't** have to read
this doc.

<div id="toc">
</div>

## Change in Syntax

You're unlikely to hit these problems, but they're worth noting.

### `if ( )` and `while ( )` take expressions, not subshells

Code like `if ( ls )` is valid shell, but it's almost always a
misunderstanding.  Parentheses mean **subshell**, not grouping as in C or
Python.

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

Note that in Oil, the idiom of running commands in a different directory
doesn't require subshells:

No:

    ( cd /tmp; echo $PWD )
    echo $PWD  # still the original value

Yes:

    cd /tmp {
      echo $PWD 
    }
    echo $PWD  # restored


- `shopt --set parse_paren` is part of group `oil:upgrade`

### `@()` is spliced command sub, not extended glob 

Oil doesn't have explicit word splitting, so we want `@(seq 3)` to be
consistent with `$(hostname)`.  They're related in the same way that `@myarray`
and `$mystr` are.

This means that `@()` is no longer extended glob, and `,()` is an alias.

No:

    echo @(*.cc|*.h)

Use this Oil alias instead:

    echo ,(*.cc|*.h)

- `shopt --set parse_at` is part of group `oil:upgrade`

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

- `shopt --set parse_raw_string` is part of group `oil:upgrade`

## Deprecated

### Extended Globs in Commands and Arrays

Like regular globs, the extended glob syntax is used in two ways:

1. Pattern matching 
   - `case` 
   - Bash boolean expressions like `[[ x == !(*.cc|*.h) ]]`
2. Word Evaluation
   - commands like `cp !(*.cc|*.h) /tmp`
   - arrays like `local -a myarray=( !(*.cc|*.h) )`

Extended globs are **not** implemented in [Simple Word
Evaluation](simple-word-eval.html), so you can't use them in the second way.

Instead of extended globs, use the `find` command or [Egg
expressions](eggex.html).

- `shopt --set simple_word_eval` is part of group `oil:upgrade`

## More Quotes May Be Needed

Most of the following syntax changes are unlikely.

`shopt --set parse_at`

- In Oil, `@` is used to splice arrays.  If you want to pass a string `@foo` to
  a command, then quote it like `'@foo'`.

`shopt --set parse_brace`

- Braces after commands start block arguments.  If you want to change to a
  directory named `{`, then quote it like `cd '{'`.

`shopt --set parse_equals`

- `x = 42` is a "bare assignment" or attribute.  If you want to pass `=` to a
  command `x`, then quote it like `x '='`.

Unconditionally changed:

- To avoid confusion with Oil's `=` operator, `=x` is disallowed as the first
  word in a command.
  - Quote it like `'=x'` if that's what you mean.
- Oil has new keywords like `proc`, `const`, `var`, and `setvar`.  To
  use them as command names (discouraged), quote them like `'proc'`.

## Summary

This concludes the list of features that's broken when you upgrade from OSH to
Oil.  We tried to keep this list as small as possible.

There are other features that are **discouraged**, like `$(( x + 1 ))`, `(( i++
))`, `[[ $s =~ $pat ]]`, and `${s%%prefix}`.  These have better alternatives in
the Oil expression language, but they can still be used.  See [Oil vs. Shell
Idioms](idioms.html).

## Related

- [Known Differences Between OSH and Other Shells](known-differences.html)


