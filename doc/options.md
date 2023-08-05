---
in_progress: yes
default_highlighter: oil-sh
---

Global Shell Options: Turning OSH into YSH
==========================================

(Until 2023, YSH was called the "Oil language".  This doc will be updated.)

This document describes global shell options, which look like this:

    shopt --set strict_backslash  # YSH style
    shopt --set ysh:upgrade       # A whole group of options
    set -o errexit                # Bourne shell style

They can affect parsing or execution, and are used to gradually turn the
[OSH]($xref:OSH) into the [YSH]($xref:YSH).

For example, YSH doesn't have word splitting on whitespace.  Instead, it use
[Simple Word Evaluation](simple-word-eval.html).  (Blog: [Oil Doesn't Require
Quoting
Everywhere](https://www.oilshell.org/blog/2021/04/simple-word-eval.html)).

This isn't the **only** use for options, but it's an important one.

<div id="toc">
</div>

## What Every User Should Know (2 minutes)

When you run `bin/osh`, the **option groups** `strict:all` and `ysh:upgrade` are
"canned settings" that relieve you of having to know about dozens of shell
options.

Running `bin/ysh` is equivalent to using `shopt --set ysh:all` in `bin/osh`.

Let's look at three examples.

### Strict

If you put this line at the top of your shell script, it will still **run under
other shells**, but OSH will act as sort of a "runtime linter":

    # Abort on more errors, but fixes will still be compatible
    shopt -s strict:all 2>/dev/null || true 

### Upgrade

If you want to upgrade a script, and don't care about running under other
shells, use this:

    # Start enabling YSH syntax and semantics
    shopt --set ysh:upgrade

This second line may break a few things, but is designed to be an easy upgrade.
See [What Breaks When You Upgrade to Oil](upgrade-breakage.html).

### Oil

If you're writing a new script, you can use `bin/ysh` to get **all**
enhancements.  Typically you use a shebang line like this:

    #!/usr/bin/env ysh

That's all most users need to know.  For more details, see the wiki page:
[Gradually Upgrading Shell to Oil]($wiki).

## Using Shell Options

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

You typically invoke the `shopt` builtin at the top of a script, but you
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
    shopt -p ysh:upgrade          # print options in the given group

TODO: Oil should enable `shopt --print` for all options.  It should have a flat
list.

## Kinds of Options, With Examples

*Option groups* like `ysh:upgrade` are baked into the interpreter.  What follows
is an informal list of *kinds* of options, which are different categorization:

- Groups: How much of Oil do you want to use?
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
  - `simple_word_eval` is the most aggressive

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

    var words = :| ale bean |
    write -- @words
    # =>
    # ale
    # bean

and inline function calls:

    write -- @[split('ale bean')]
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

## List of Options

### Selected Options

`strict_arith`.  Strings that don't look like integers cause a fatal error in
arithmetic expressions.

`strict_argv`.  Empty `argv` arrays are disallowed (because there's no
practical use for them).  For example, the second statement in `x=''; $x`
results in a fatal error.

`strict_array`. No implicit conversions between string an array.  In other
words, turning this on gives you a "real" array type.

`strict_control_flow`. `break` and `continue` outside of a loop are fatal
errors.

`simple_eval_builtin`.  The `eval` builtin takes exactly **one** argument.  It
doesn't concatenate its arguments with spaces, or accept zero arguments.

`strict_word_eval`.  More word evaluation errors are fatal.

- String slices with negative arguments like `${s: -1}` and `${s: 1 : -1}`
  result in a fatal error.  (NOTE: In array slices, negative start indices are
  allowed, but negative lengths are always fatal, regardless of
  `strict_word_eval`.)
- UTF-8 decoding errors are fatal when computing lengths (`${#s}`) and slices.

For options affecting exit codes, see the [error handling
doc](error-handling.html).

### Complete List

See the [Chapter on Global Shell Options](ref/chap-option.html) in the
reference.

## FAQ: Aren't Global Variables Bad?

Options are technically globals, but Oil controls them in 2 ways:

1. It has scoped mutation with Ruby-like [blocks](proc-block-func.html).
    - Example: `shopt --unset errexit { false }`
2. Like all Bourne shells, Oil uses process-based concurrency.  It doesn't have
   shared memory.

## Related Documents

- Up: [Interpreter State](interpreter-state.html), which is under construction

