---
default_highlighter: oil-sh
---

What Breaks When You Upgrade to Oil
===================================

Only a few things break when you put this at the top of a shell script:

    shopt --set oil:upgrade

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

You can also use `bin/osh` indefinitely, in which case you **don't** need to
read this doc.  [OSH]($xref:osh-language) is a highly compatible Unix shell.

## Syntax Changes

Now onto the breakages.  Most of them are **unlikely**, but worth noting.

### `if ( )` and `while ( )` take expressions, not subshell commands

Option `parse_paren`.  Code like `if ( ls /tmp )` is valid shell, but it's almost always a **misuse**
of the language.  Because parentheses mean **subshell**, not grouping as in C or
Python.

In Oil the parens in `if (x > 0)` denote a true/false expression.


### Simple Word Eval, no implicit split/glob/maybe

Variables are expanded reliably *without* implicitly and often surprisingly getting
split, globbed, and omitted if empty (sensible default).

Where string-magic-based, i.e. not array/dict-based, operation is really wanted or needed,
use an explicit `@split()` (shortcut `@`), `@glob()`,`@maybe()` or the non-splitting `$` counterparts of the last two.


### `@()` is spliced command sub, not extended glob 

As Oil doesn't have implicit word splitting, we want `@(seq 3)` to be the splitting
variant of the command sub `$(seq 3)`.  They're related in the same way as `@myarray`
and `$mystr` are.

This means that `@()` is no longer an extended glob, however `,()` is its substitute.

No:

    echo @(*.cc|*.h)

Use this Oil alias instead:

    echo ,(*.cc|*.h)

(Option `parse_at` is part of group `oil:upgrade`.)

### `r'c:\Users\'` is a raw string, not joined strings

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


## Disabled Syntax, improved alternatives

### No Extended Globs in Simple Word Evaluation

Like regular globs, the extended glob syntax is used in two ways:

1. Pattern matching 
   - `case` 
   - Bash boolean expressions like `[[ x == !(*.cc|*.h) ]]`
2. Word Evaluation
   - commands like `cp !(*.cc|*.h) /tmp`
   - array definitions like `local -a myarray=( !(*.cc|*.h) )`
   - Shell-style `for` loops

Extended globs are **not** supported in [Simple Word
Evaluation](simple-word-eval.html), so you can't use them in the second way
after upgrading.

You may want to use the `find` command or [Egg expressions](eggex.html)
instead.

(Option `simple_word_eval` is part of group `oil:upgrade`.)

## Few Quotes May Be Needed (rare occasions)

### `@foo` as command or argument (now splice)

Option `parse_at`.  In Oil, `@` is used to splice arrays.  To pass a string
`@foo` to a command, quote it like `'@foo'`.

### `{` as argument (now block)

Option `parse_brace`.  Braces after commands start block arguments.  To change
to a directory named `{`, quote it like `cd '{'`.

### `=` as argument within blocks (bare assignments)

Option `parse_equals`.  A statement like `x = 42` within a block is a "bare assignment" of a constant or
attribute.  To pass `=` to a command `foo`, quote it as in `foo '='`.

### New first-word keywords (`proc`, `var` etc.)

Oil has new keywords like `proc`, `const`, `var`, `setvar`, and `=`.  To use them
as command names, quote them like `'proc'`.

### `=foo` as command (too similar to `= foo`)

To avoid confusion with Oil's `=` operator, words starting with `=` can't be the first word in a command.
To invoke such commands, quote them like `'=foo'`.

There is very little reason for external commands like `'proc'` or `'=foo'`, so you
will likely never run into these!




## Summary

This concludes the list of features that's broken when you upgrade from OSH to
Oil.  We tried to keep this list as small as possible.

There are other features that are **discouraged**, like `$(( x + 1 ))`, `(( i++
))`, `[[ $s =~ $pat ]]`, and `${s%%prefix}`.  These have better alternatives in
the Oil expression language, but they can still be used.  See [Oil vs. Shell
Idioms](idioms.html).

Also related: [Known Differences Between OSH and Other
Shells](known-differences.html).


