---
in_progress: yes
default_highlighter: oil-sh
---

Global Shell Options: Turning OSH into Oil
==========================================

This document describes global shell options, which look like this:

    shopt --set strict_backslash  # Oil style
    set -o errexit                # Bourne shell style

They can affect parsing or execution, and are used to gradually turn
the [OSH language]($xref:osh-language) into the [Oil
language]($xref:oil-language).

For example, Oil doesn't have word splitting on whitespace, use [Simple Word
Evaluation](simple-word-eval.html) by default.  (Blog: [Oil Doesn't Require
Quoting
Everywhere](https://www.oilshell.org/blog/2021/04/simple-word-eval.html)).

This isn't the **only** use for them, but it's one of the main uses.

<!--

Notes:
- OSH manual describes some options.  Could move them here.
- Copy in frmo quick ref
-->

<div id="toc">
</div>

## Quick Start

The **option groups** `strict:all` and `oil:basic` are "canned settings" that
relieve you of having to know about dozens of shell options.

If you put this line at the top of your shell script, it will still **run under
other shells**, but OSH will act as sort of a "runtime linter":

    # Abort on more errors, but fixes will still be compatible
    shopt -s strict:all 2>/dev/null || true 

If you don't care about running under other shells, use this:

    # Start enabling Oil syntax and semantics
    shopt --set oil:basic

This second line may break a few things, but is designed to be an easy upgrade.
See [Shell Language Deprecations](deprecations.html).

Use `bin/oil` for a brand new Oil script, opting into **all** enhancements.
Your shebang line might be `#!/usr/bin/env oil`.  This is the equivalent of
`shopt --set oil:all`.

That's all most users need to know.  For more details, see the wiki page:
[Gradually Upgrading Shell to Oil]($wiki).

## FAQ: Aren't Global Variables Bad?

- Oil adds scope with Ruby-like [blocks](proc-block-func.html).
- Like all Bourne shells, Oil uses process-based concurrency.  It doesn't have
  shared memory.

## Usage

There are several different ways of using shell options.

### Preferred Style

Oil has **long flags** for readability, which are preferred:

    shopt --set errexit
    shopt --unset errexit

It also allows **scoped** options:

    shopt --unset errexit {
      false    # non-zero status ignored
      ls /bad
    }
    false  # original setting restored

### Bourne Shell Style

For compatibility, these styles works in Oil:

    set -e          # abort script on non-zero exit exit code
    set +e          # turn it off

    set -o errexit  # a more readable version of the above
    set +o errexit 

[Bash]($xref:bash)-style option with `shopt`:

    shopt -s nullglob  # turn it on
    shopt -u nullglob  # turn it off

### Setting Options Via Command Line Flags

You typically invoke the `shopt` builtin at the the top of a script, but you
can also set options at the command line:

    osh -O errexit -c 'shopt -p -o'  # turn on Bourne option
    osh +O errexit -c 'shopt -p -o'  # turn off Bourne option

    osh -O strict_tilde -c 'shopt -p'  # turn on Oil option
    osh +O strict_tilde -c 'shopt -p'  # turn off Oil option

### Inspecting Option State

Shell has many ways to do this, like:

    set -o                      # print all Bourne shell options
    shopt -p                    # print all bash options
    shopt -p nullglob failglob  # print selected options

TODO: Oil should enable `shopt --print` for all options.  It should have a flat
list.

## Option Groups Are Named

To let you turn them all on or off at once.

### List of Option Groups

- `strict:all`: Help you find bugs.  Do NOT break things to improve style.
- `oil:basic`: Allow using Oil features that are unlikely to break something,
  or have an easy fix (example: `@foo` -> `'@foo'`, and `()` -> `forkwait`).
  Again, do NOT break things to improve style.
- `oil:all`: Allow even more Oil features.  And also break things to improve
  style.  (Example: `simple_eval_builtin`).

TODO: Do we need `simple:all`?

### Example: `oil:all`

Runnig `bin/oil` is equivalent to

    shopt --set oil:all

It turns on:

- `errexit`, `nounset` (`sh` modes to get more errors)
- `pipefail` and `inherit_errexit` (`bash` modes to get more errors)
- Oil modes:
  - `simple_word_eval` (subsumes `nullglob` that `strict:all` includes)
  - `command_sub_errexit`
  - `strict_*` (`strict_array`, etc.)
  - `parse_*` (`parse_at`, etc.)

## Kinds of Options, With Examples

This is NOT FORMAL like GROUPS.  GROUPS AND Kinds are different!

They are orthogonal axes.

- Groups: how much of Oil do you want to use?
- Kinds: Does this option affect parsing behavior, runtime behavior, or
  something else?

### Naming Conventions

- `parse_*`: Change parsing.
  - enable new features: `parse_at`, `parse_equals`.
  - turn off to reject bad or old code: `parse_backticks`, `parse_backslash`,
    `parse_dollar`.
- `strict_*`: Fail at runtime instead of ignoring the bug like bash.
  - `${#s}` on invalid unicode is a runtime error.
  - `~typo` is a runtime error.
- `simple_*`: Break things to improve style.
  - `simple_eval_builtin`, `simple_echo`.
  - `simple_word_eval` is the most aggresive

### Strict Options Produce More Errors

These options produce more **programming errors**.  Importantly, the resulting
program is still compatible with other shells.

For example, `shopt -s strict_array` produces runtime errors when you confuse
strings and arrays.  After you fix these problems, your program will still run
correctly under `bash`.

In contrast, if you set `shopt -s simple_word_eval` (an option that doesn't
start with `strict_`), the semantics of your program have changed, and you can
**no longer** run it under other shells.  It's considered an "Oil option": by
setting it, you're using parts of the Oil language.

### Parse Options Change Syntax

Options that affect parsing start with `parse_`.  For example, `shopt -s
parse_at` enables **splicing** with the `@` character:

    var words = %(ale bean)
    write -- @words
    # =>
    # ale
    # bean

and inline function calls:

    write -- @split('ale bean')
    # =>
    # ale
    # bean

As another example, `shopt --set parse_brace` takes over the `{ }` characters.
Specifically, it does three things:

1. Allow builtins like `cd` to take a block (discussed in a [Zulip
  thread](https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/cd.20now.20takes.20a.20Ruby-like.20block))
2. Control flow like `if`, `case`, `for`, and `while/until`, use curly brace
   delimiters instead of `then/fi`, `do/done`, etc.  See below.
3. To remove confusion, braces must be balanced inside a word.  echo `foo{` is
   an error.  It has to be `echo foo\{` or `echo 'foo{'`.
   - In a correct brace expansion, they're always balanced: `{pea,coco}nut`
   - This is so that the syntax errors are better when you forget a space.

<!--
Test cases start here: <https://github.com/oilshell/oil/blob/master/spec/oil-options.test.sh#L257>
-->

Here's idiomatic Oil syntax after `parse_brace`:

    cd /tmp {
      echo $PWD
    }

    if test -d foo {
      echo 'dir'
    } elif test -f foo {
      echo 'file'
    } else {
       echo 'neither'
    }

    # Single line statements are supported:
    if test -d / { echo 'dir' } else { echo 'nope' }

    while true {
      echo hi
      break
    }

    # Loop over words
    for x in ale bean *.sh {
      echo $x
    }

    # Replace 'in' with {, and 'esac' with }
    case $x {
      *.py)
        echo python
        ;;
      *.sh)
        echo shell
        ;;
    }

What's the motivation for this?  Mainly familiarity: I hear a lot of feedback
that nobody can remember how to write if statements in shell.  See [The
Simplest Explanation of
Oil](//www.oilshell.org/blog/2020/01/simplest-explanation.html).

<!--

There are also **expression** variants of these constructs:

    if (x > 0) {
      echo hi
    }

    while (x > 0) {
      echo hi
    }

(`for` and `case` to come later.)

-->


### Runtime Options Change Behavior

- `simple_echo`.  Changes the flags accepted by the `echo` builtin, and style of flag parsing.
  See the `Builtins > echo` below.
- `simple_word_eval`.  Word evaluation consists of one stage rather than three:
  - No word splitting or empty elision.  (In other words, arity isn't data-dependent.)
  - Static globbing, but no dynamic globbing.  (In other words, data isn't re-parsed as code.)
  - This option is intended to be implemented by other shells.

TODO: copy examples from spec tests

    echo $dir/*.py

- `command_sub_errexit`.  A error in a command sub can cause the **parent
   shell** to exit fatally.  Also see `inherit_errexit` and `strict_errexit`.

## Complete List of Options

These documents have a short description of each option:

- [OSH Help Topics > option](osh-help-topics.html#option)
- [Oil Help Topics > option](oil-help-topics.html#option)

(TODO: longer descriptions.)

## Related Documents

- Up: [Interpreter State](interpreter-state.html), which is under construction)

