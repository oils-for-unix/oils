---
default_highlighter: oils-sh
---

YSH Fixes Shell's Error Handling (`errexit`)
============================================

<style>
  .faq {
    font-style: italic;
    color: purple;
  }

  /* copied from web/blog.css */
  .attention {
    text-align: center;
    background-color: #DEE;
    padding: 1px 0.5em;

    /* to match p tag etc. */
    margin-left: 2em;
  }
</style>

YSH is unlike other shells:

- It never silently ignores an error, and it never loses an exit code.
- There's no reason to write an YSH script without `errexit`, which is on by
  default.

This document explains how YSH makes these guarantees.  We first review shell
error handling, and discuss its fundamental problems.  Then we show idiomatic
YSH code, and look under the hood at the underlying mechanisms.

[file a bug]: https://github.com/oilshell/oil/issues

<div id="toc">
</div>

## Review of Shell Error Handling Mechanisms

POSIX shell has fundamental problems with error handling.  With `set -e` aka
`errexit`, you're [damned if you do and damned if you don't][bash-faq].

GNU [bash]($xref) fixes some of the problems, but **adds its own**, e.g. with
respect to process subs, command subs, and assignment builtins.

YSH fixes all the problems by adding new builtin commands, special variables,
and global options.  But you see a simple interface with `try` and `_status`.

Let's review a few concepts before discussing YSH.

### POSIX Shell

- The special variable `$?` is the exit status of the "last command".  It's a
  number between `0` and `255`.
- If `errexit` is enabled, the shell will abort if `$?` is nonzero.
  - This is subject to the *Disabled `errexit` Quirk*, which I describe below.

These mechanisms are fundamentally incomplete.

### Bash

Bash improves error handling for pipelines like `ls /bad | wc`.

- `${PIPESTATUS[@]}` stores the exit codes of all processes in a pipeline.
- When `set -o pipefail` is enabled, `$?` takes into account every process in a
  pipeline.
  - Without this setting, the failure of `ls` would be ignored.
- `shopt -s inherit_errexit` was introduced in bash 4.4 to re-introduce error
  handling in command sub child processes.  This fixes a bash-specific bug.

But there are still places where bash will lose an exit code.

&nbsp;

## Fundamental Problems

Let's look at **four** fundamental issues with shell error handling.  They
underlie the **nine** [shell pitfalls enumerated in the
appendix](#list-of-pitfalls).

### When Is `$?` Set?

Each external process and shell builtin has one exit status.  But the
definition of `$?` is obscure: it's tied to the `pipeline` rule in the POSIX
shell grammar, which does **not** correspond to a single process or builtin.

We saw that `pipefail` fixes one case:

    ls /nonexistent | wc   # 2 processes, 2 exit codes, but just one $?

But there are others:

    local x=$(false)                 # 2 exit codes, but just one $?
    diff <(sort left) <(sort right)  # 3 exit codes, but just one $?

This issue means that shell scripts fundamentally **lose errors**.  The
language is unreliable.

### What Does `$?` Mean?

Each process or builtin decides the meaning of its exit status independently.
Here are two common choices:

1. **The Failure Paradigm**
   - `0` for success, or non-zero for an error.
   - Examples: most shell builtins, `ls`, `cp`, ...
1. **The Boolean Paradigm**
   - `0` for true, `1` for false, or a different number like `2` for an error.
   - Examples: the `test` builtin, `grep`, `diff`, ...

New error handling constructs in YSH deal with this fundamental inconsistency.

### The Meaning of `if`

Shell's `if` statement tests whether a command exits zero or non-zero:

    if grep class *.py; then
      echo 'found class'
    else
      echo 'not found'  # is this true?
    fi

So while you'd expect `if` to work in the boolean paradigm, it's closer to
the failure paradigm.  This means that using `if` with certain commands can
cause the *Error or False Pitfall*:

    if grep 'class\(' *.py; then  # grep syntax error, status 2
      echo 'found class('
    else
      echo 'not found is a lie'
    fi
    # => grep: Unmatched ( or \(
    # => not found is a lie

That is, the `else` clause conflates grep's **error** status 2 and **false**
status 1.

Strangely enough, I encountered this pitfall while trying to disallow shell's
error handling pitfalls in YSH!  I describe this in another appendix as the
"[meta pitfall](#the-meta-pitfall)".

### Design Mistake: The Disabled `errexit` Quirk

There's more bad news about the design of shell's `if` statement.  It's subject
to the *Disabled `errexit` Quirk*, which means when you use a **shell function**
in a conditional context, errors are unexpectedly **ignored**.

That is, while `if ls /tmp` is useful, `if my-ls-function /tmp` should be
avoided.  It yields surprising results.

I call this the *`if myfunc` Pitfall*, and show an example in [the
appendix](#disabled-errexit-quirk-if-myfunc-pitfall).

We can't fix this decades-old bug in shell.  Instead we disallow dangerous code
with `strict_errexit`, and add new error handling mechanisms.

&nbsp;

## YSH Error Handling: The Big Picture 

We've reviewed how POSIX shell and bash work, and showed fundamental problems
with the shell language.

But when you're using YSH, **you don't have to worry about any of this**!

### YSH Fails On Every Error

This means you don't have to explicitly check for errors.  Examples:

    shopt --set ysh:upgrade     # Enable good error handling in bin/osh
                                # It's the default in bin/ysh.
    shopt --set strict_errexit  # Disallow bad shell error handling.
                                # Also the default in bin/ysh.

    local date=$(date X)        # 'date' failure is fatal
    # => date: invalid date 'X' 

    echo $(date X)              # ditto

    echo $(date X) $(ls > F)    # 'ls' isn't executed; 'date' fails first

    ls /bad | wc                # 'ls' failure is fatal

    diff <(sort A) <(sort B)    # 'sort' failure is fatal

On the other hand, you won't experience this problem caused by `pipefail`:

    yes | head                 # doesn't fail due to SIGPIPE

The details are explained below.

### `try` Handles Command and Expression Errors

You may want to **handle failure** instead of aborting the shell.  In this
case, use the `try` builtin and inspect the `_status` variable it sets.

    try {                 # try takes a block of commands
      ls /etc
      ls /BAD             # it stops at the first failure
      ls /lib
    }                     # After try, $? is always 0
    if (_status !== 0) {  # Now check _status
      echo 'failed'
    }

Note that:

- The `_status` variable is different than `$?`.
  - The leading `_` is a PHP-like convention for special variables /
    "registers" in YSH.
- Idiomatic YSH programs don't look at `$?`.

You can omit `{ }` when invoking a single command.  Here's how to invoke a
function without the *`if myfunc` Pitfall*:

    try myfunc            # Unlike 'myfunc', doesn't abort on error
    if (_status !== 0) {
      echo 'failed'
    }

You also have fine-grained control over every process in a pipeline:

    try {
      ls /bad | wc
    }
    write -- @_pipeline_status  # every exit status

And each process substitution:

    try {
      diff <(sort left.txt) <(sort right.txt)
    }
    write -- @_process_sub_status  # every exit status


&nbsp;

<div class="attention">

See [YSH vs. Shell Idioms > Error Handling](idioms.html#error-handling) for
more examples.

</div>

&nbsp;

Certain expressions produce fatal errors, like:

    var x = 42 / 0  # divide by zero will abort shell

The `try` builtin also handles them:

    try {
       var x = 42 / 0
    }
    if (_status !== 0) {
      echo 'divide by zero'
    }

More examples: 

- Index out of bounds `a[i]` 
- Nonexistent key `d->foo` or `d['foo']`.

Such expression evaluation errors result in status `3`, which is an arbitrary non-zero
status that's not used by other shells.  Status `2` is generally for syntax
errors and status `1` is for most runtime failures.

### `boolstatus` Enforces 0 or 1 Status

The `boolstatus` builtin addresses the *Error or False Pitfall*:

    if boolstatus grep 'class' *.py {  # may abort the program
      echo 'found'      # status 0 means 'found'
    } else {
      echo 'not found'  # status 1 means 'not found'
    }

Rather than confusing **error** with **false**, `boolstatus` will abort the
program if `grep` doesn't return 0 or 1.

You can think of this as a shortcut for

    try grep 'class' *.py
    case $_status {
      (0) echo 'found'
          ;;
      (1) echo 'not found'
          ;;
      (*) echo 'fatal'
          exit $_status
          ;;
    }

### FAQ on Language Design

<div class="faq">

Why is there `try` but no `catch`?

</div>

First, it offers more flexibility:

- The handler usually inspects `_status`, but it may also inspect
  `_pipeline_status` or `_process_sub_status`.
- The handler may use `case` instead of `if`, e.g. to distinguish true / false
  / error.

Second, it makes the language smaller:

- `try` / `catch` would require specially parsed keywords.  But our `try` is a
  shell builtin that takes a block, like `cd` or `shopt`.
- The builtin also lets us write either `try ls` or `try { ls }`, which is hard
  with a keyword.

Another way to remember this is that there are **three parts** to handling an
error, each of which has independent choices:

1. Does `try` take a simple command or a block?  For example, `try ls` versus
   `try { ls; var x = 42 / n }`
2. Which status do you want to inspect?
3. Inspect it with `if` or `case`?  As mentioned, `boolstatus` is a special
   case of `try / case`.

<div class="faq">

Why is `_status` different from `$?`

</div>

This avoids special cases in the interpreter for `try`, which is again a
builtin that takes a block.

The exit status of `try` is always `0`.  If it returned a non-zero status, the
`errexit` rule would trigger, and you wouldn't be able to handle the error!

Generally, [errors occur *inside* blocks, not
outside](proc-block-func.html#errors).

Again, idiomatic YSH scripts never look at `$?`, which is only used to trigger
shell's `errexit` rule.  Instead they invoke `try` and inspect `_status` when
they want to handle errors.

<div class="faq">

Why `boolstatus`?  Can't you just change what `if` means in YSH?

</div>

I've learned the hard way that when there's a shell **semantics** change, there
must be a **syntax** change.  In general, you should be able to read code on
its own, without context.

Readers shouldn't have to constantly look up whether `ysh:upgrade` is on.  There
are some cases where this is necessary, but it should be minimized.

Also, both `if foo` and `if boolstatus foo` are useful in idiomatic YSH code.

&nbsp;

<div class="attention">

**Most users can skip to [the summary](#summary).**  You don't need to know all
the details to use YSH.

</div>

&nbsp;

## Reference: Global Options


Under the hood, we implement the `errexit` option from POSIX, bash options like
`pipefail` and `inherit_errexit`, and add more options of our
own.  They're all hidden behind [option groups](options.html) like `strict:all`
and `ysh:upgrade`.

The following sections explain new YSH options.

### `command_sub_errexit` Adds More Errors

In all Bourne shells, the status of command subs is lost, so errors are ignored
(details in the [appendix](#quirky-behavior-of)).  For example:

    echo $(date X) $(date Y)  # 2 failures, both ignored
    echo                      # program continues

The `command_sub_errexit` option makes both `date` invocations an an error.
The status `$?` of the parent `echo` command will be `1`, so if `errexit` is
on, the shell will abort.

(Other shells should implement `command_sub_errexit`!)

### `process_sub_fail` Is Analogous to `pipefail`

Similarly, in this example, `sort` will fail if the file doesn't exist.

    diff <(sort left.txt) <(sort right.txt)  # any failures are ignored

But there's no way to see this error in bash.  YSH adds `process_sub_fail`,
which folds the failure into `$?` so `errexit` can do its job.

You can also inspect the special `_process_sub_status` array variable to
implement custom error logic.

### `strict_errexit` Flags Two Problems

Like other `strict_*` options, YSH `strict_errexit` improves your shell
programs, even if you run them under another shell like [bash]($xref)!  It's
like a linter *at runtime*, so it can catch things that [ShellCheck][] can't.

[ShellCheck]: https://www.shellcheck.net/

`strict_errexit` disallows code that exhibits these problems:

1. The `if myfunc` Pitfall
1. The `local x=$(false)` Pitfall

See the appendix for examples of each.

#### Rules to Prevent the `if myfunc` Pitfall

In any conditional context, `strict_errexit` disallows:

1. All commands except `((`, `[[`, and some simple commands (e.g. `echo foo`).
   - Detail: `! ls` is considered a pipeline in the shell grammar.  We have to
     allow it, while disallowing `ls | grep foo`.
2. Function/proc invocations (which are a special case of simple
   commands.)
3. Command sub and process sub (`shopt --unset allow_csub_psub`)

This means that you should check the exit status of functions and pipeline
differently.  See [Does a Function
Succeed?](idioms.html#does-a-function-succeed), [Does a Pipeline
Succeed?](idioms.html#does-a-pipeline-succeed), and other [YSH vs. Shell
Idioms](idioms.html).

#### Rule to Prevent the `local x=$(false)` Pitfall

- Command Subs and process subs are disallowed in assignment builtins: `local`,
  `declare` aka `typeset`, `readonly`, and `export`.

No:

    local x=$(false)

Yes:

    var x = $(false)   # YSH style

    local x            # Shell style
    x=$(false)

### `sigpipe_status_ok` Ignores an Issue With `pipefail`

When you turn on `pipefail`, you may inadvertently run into this behavior:

    yes | head
    # => y
    # ...

    echo ${PIPESTATUS[@]}
    # => 141 0

That is, `head` closes the pipe after 10 lines, causing the `yes` command to
**fail** with `SIGPIPE` status `141`.

This error shouldn't be fatal, so OSH has a `sigpipe_status_ok` option, which
is on by default in YSH.

### `verbose_errexit`

When `verbose_errexit` is on, the shell prints errors to `stderr` when the
`errexit` rule is triggered.

### FAQ on Options

<div class="faq">

Why is there no `_command_sub_status`?  And why is `command_sub_errexit` named
differently than `process_sub_fail` and `pipefail`?

</div>

Command subs are executed **serially**, while process subs and pipeline parts
run **in parallel**.

So a command sub can "abort" its parent command, setting `$?` immediately.
The parallel constructs must wait until all parts are done and save statuses in
an array.  Afterward, they determine `$?` based on the value of `pipefail` and
`process_sub_fail`.

<div class="faq">

Why are `strict_errexit` and `command_sub_errexit` different options?

</div>

Because `shopt --set strict:all` can be used to improve scripts that are run
under other shells like [bash]($xref).  It's like a runtime linter that
disallows dangerous constructs.

On the other hand, if you write code with `command_sub_errexit` on, it's
impossible to get the same failures under bash.  So `command_sub_errexit` is
not a `strict_*` option, and it's meant for code that runs only under YSH.

<div class="faq">

What's the difference between bash's `inherit_errexit` and YSH
`command_sub_errexit`?  Don't they both relate to command subs?

</div>

- `inherit_errexit` enables failure in the **child** process running the
  command sub.
- `command_sub_errexit` enables failure in the **parent** process, after the
  command sub has finished.

&nbsp;

## Summary

YSH uses three mechanisms to fix error handling once and for all.

It has two new **builtins** that relate to errors:

1. `try` lets you explicitly handle errors when `errexit` is on.
1. `boolstatus` enforces a true/false meaning.  (This builtin is less common).

It has three **special variables**:

1. The `_status` integer, which is set by `try`.
   - Remember that it's distinct from `$?`, and that idiomatic YSH programs
     don't use `$?`.
1. The `_pipeline_status` array (another name for bash's `PIPESTATUS`)
1. The `_process_sub_status` array for process substitutions.

Finally, it supports all of these **global options**:

- From POSIX shell:
  - `errexit`
- From [bash]($xref):
  - `pipefail`
  - `inherit_errexit` aborts the child process of a command sub.
- New:
  - `command_sub_errexit` aborts the parent process immediately after a failed
    command sub.
  - `process_sub_fail` is analogous to `pipefail`.
  - `strict_errexit` flags two common problems.
  - `sigpipe_status_ok` ignores a spurious "broken pipe" failure.
  - `verbose_errexit` controls whether error messages are printed.

When using `bin/osh`, set all options at once with `shopt --set ysh:upgrade
strict:all`.  Or use `bin/ysh`, where they're set by default.

<!--
Related 2020 blog post [Reliable Error
Handling](https://www.oilshell.org/blog/2020/10/osh-features.html#reliable-error-handling).
-->


## Related Docs

- [YSH vs. Shell Idioms](idioms.html) shows more examples of `try` and `boolstatus`.
- [Shell Idioms](shell-idioms.html) has a section on fixing `strict_errexit`
  problems in Bourne shell.

Good articles on `errexit`:

- Bash FAQ: [Why doesn't `set -e` do what I expected?][bash-faq]
- [Bash: Error Handling](http://fvue.nl/wiki/Bash:_Error_handling) from
  `fvue.nl`

[bash-faq]: http://mywiki.wooledge.org/BashFAQ/105

Spec Test Suites:

- <https://www.oilshell.org/release/latest/test/spec.wwz/survey/errexit.html>
- <https://www.oilshell.org/release/latest/test/spec.wwz/survey/errexit-oil.html>

These docs aren't about error handling, but they're also painstaking
backward-compatible overhauls of shell!

- [Simple Word Evaluation in Unix Shell](simple-word-eval.html)
- [Egg Expressions (YSH Regexes)](eggex.html)

For reference, this work on error handling was described in [Four Features That
Justify a New Unix
Shell](https://www.oilshell.org/blog/2020/10/osh-features.html) (October 2020).
Since then, we changed `try` and `_status` to be more powerful and general.

&nbsp;

## Appendices

### List Of Pitfalls

We mentioned some of these pitfalls:

1. The `if myfunc` Pitfall, caused by the Disabled `errexit` Quirk (`strict_errexit`)
1. The `local x=$(false)` Pitfall (`strict_errexit`)
1. The Error or False Pitfall (`boolstatus`, `try` / `case`)
   - Special case: When the child process is another instance of the shell, the
     Meta Pitfall is possible.
1. The Process Sub Pitfall (`process_sub_fail` and `_process_sub_status`)
1. The `yes | head` Pitfall (`sigpipe_status_ok`)

There are two pitfalls related to command subs:

6. The `echo $(false)` Pitfall (`command_sub_errexit`)
6. Bash's `inherit_errexit` pitfall.
   - As mentioned, this bash 4.4 option fixed a bug in earlier versions of
     bash.  YSH reimplements it and turns it on by default.

Here are two more pitfalls that don't require changes to YSH:

8. The Trailing `&&` Pitfall
   - When `test -d /bin && echo found` is at the end of a function, the exit
     code is surprising.
   - Solution: always use `if` rather than `&&`.
   - More reasons: the `if` is easier to read, and `&&` isn't useful when
     `errexit` is on.
8. The surprising return value of `(( i++ ))`, `let`, `expr`, etc.
   - Solution: Use `i=$((i + 1))`, which is valid POSIX shell.
   - In YSH, use `setvar i += 1`.

#### Example of `inherit_errexit` Pitfall

In bash, `errexit` is disabled in command sub child processes:

    set -e
    shopt -s inherit_errexit  # needed to avoid 'touch two'
    echo $(touch one; false; touch two)

Without the option, it will touch both files, even though there is a failure
`false` after the first.

#### Bash has a grammatical quirk with `set -o failglob`

This isn't a pitfall, but a quirk that also relates to errors and shell's
**grammar**.  Recall that the definition of `$?` is tied to the grammar.

Consider this program:

    set -o failglob
    echo *.ZZ        # no files match
    echo status=$?   # show failure
    # => status=1

This is the same program with a newline replaced by a semicolon:

    set -o failglob

    # Surprisingly, bash doesn't execute what's after ; 
    echo *.ZZ; echo status=$?
    # => (no output)

But it behaves differently. This is because newlines and semicolons are handled
in different **productions of the grammar**, and produce distinct syntax trees.

(A related quirk is that this same difference can affect the number of
processes that shells start!)

### Disabled `errexit` Quirk / `if myfunc` Pitfall

This quirk is a bad interaction between the `if` statement, shell functions,
and `errexit`.  It's a **mistake** in the design of the shell language.
Example:

    set -o errexit     # don't ignore errors

    myfunc() {
      ls /bad          # fails with status 1
      echo 'should not get here'
    }

    myfunc  # Good: script aborts before echo
    # => ls: '/bad': no such file or directory

    if myfunc; then  # Surprise!  It behaves differently in a condition.
      echo OK
    fi
    # => ls: '/bad': no such file or directory
    # => should not get here

We see "should not get here" because the shell **silently disables** `errexit`
while executing the condition of `if`.  This relates to the fundamental
problems above:

1. Does the function use the failure paradigm or the boolean paradigm?
2. `if` tests a single exit status, but every command in a function has an exit
   status.  Which one should we consider?

This quirk occurs in all **conditional contexts**:

1. The condition of the `if`, `while`, and `until`  constructs
2. A command/pipeline prefixed by `!` (negation)
3. Every clause in `||` and `&&` except the last.

### The Meta Pitfall

I encountered the *Error or False Pitfall* while trying to disallow other error
handling pitfalls!  The *meta pitfall* arises from a combination of the issues
discussed:

1. The `if` statement tests for zero or non-zero status.
1. The condition of an `if` may start child processes.  For example, in `if
   myfunc | grep foo`,  the `myfunc` invocation must be run in a subshell.
1. You may want an external process to use the **boolean paradigm**, and
   that includes **the shell itself**.  When any of the `strict_` options
   encounters bad code, it aborts the shell with **error** status `1`, not
   boolean **false** `1`.

The result of this fundamental issue is that `strict_errexit` is quite strict.
On the other hand, the resulting style is straightforward and explicit.
Earlier attempts allowed code that is too subtle.

### Quirky Behavior of `$?`

This is a different way of summarizing the information above.

Simple commands have an obvious behavior:

    echo hi           # $? is 0
    false             # $? is 1

But the parent process loses errors from failed command subs:

    echo $(false)     # $? is 0
                      # YSH makes it fail with command_sub_errexit

Surprisingly, bare assignments take on the value of any command subs:

    x=$(false)        # $? is 1 -- we did NOT lose the exit code

But assignment builtins have the problem again:

    local x=$(false)  # $? is 0 -- exit code is clobbered
                      # disallowed by YSH strict_errexit

So shell is confusing and inconsistent, but YSH fixes all these problems.  You
never lose the exit code of `false`.


&nbsp;

## Acknowledgments

- Thank you to `ca2013` for extensive review and proofreading of this doc.


