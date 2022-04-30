---
default_highlighter: oil-sh
---

Oil Fixes Shell's Error Handling (`errexit`)
============================================

<style>
  .faq {
    font-style: italic;
    color: purple;
  }
</style>

POSIX shell has fundamental problems with error handling.  With `set -e` aka
`errexit`, you're [damned if you do and damned if you don't][bash-faq].

GNU [bash]($xref) fixes some of the problems, but **adds its own**, e.g. with
respect to process subs, command subs, and assignment builtins.

Oil **fixes all the problems** by adding builtin commands, special variables,
and global options.  You see a new, simple interface with `try` and `_status`.
More specifically:

- Oil never silently ignores an error.  It never loses an exit code.
- There's no reason to write an Oil script without `errexit`, which is on by
  default.

If you find a shell issue that Oil doesn't handle, please [file a bug][].

This document explains how Oil makes these guarantees.  We first review shell
error handling, and discuss its fundamental problems.  Then we show idiomatic
Oil code, and look under the hood at the underlying mechanisms.

[file a bug]: https://github.com/oilshell/oil/issues

<div id="toc">
</div>

## Review of Shell Error Handling Mechanisms

### POSIX Shell

- The special variable `$?` is the exit status of the last "command".  It's a
  number between `0` and `255`.
- If `errexit` is enabled, the shell will abort if `$?` is nonzero.
  - This is subject to the *disabled `errexit` pitfall*, which I describe below.

These mechanisms are fundamentally incomplete.

### Bash

Bash improves error handling for pipelines like `ls /nonexistent | wc`.

- `${PIPESTATUS[@]}` stores the exit codes of all processes in a pipeline.
- When `set -o pipefail` is enabled, `$?` takes into account every process in
  the pipeline.  Without this setting, the failure of `ls` would be ignored.
- `shopt -s inherit_errexit` was introduced in bash 4.4 to re-introduce error
  handling in command subs.  This fixes a bash-specific bug.

But there are still places where bash will lose an exit code.

## Fundamental Problems With The Language

Without enumerating every detail, let's look at 3 fundamental issues you should
remember.

### `$?` Doesn't Correspond to Commands or Processes

Each external process and shell builtin has one exit status.  But the
definition of `$?` is obscure: it's tied to the `command` rule in the POSIX
shell grammar, which does **not** correspond to a single process or builtin.

We saw that `pipefail` fixes one case:

    ls /nonexistent | wc   # 2 processes, 2 exit codes, but just one $?

But there are others:

    local x=$(false)                 # 2 exit codes, but just one $?
    diff <(sort left) <(sort right)  # 3 exit codes, but just one $?

### What Does `$?` Mean?

Each program decides on the meaning of `$?` independently.  Here are two
conventions:

- **OK or Error**. `0` for success and non-zero for failure.
  - Example: the `cp` command
- **True, False, or Error**.  `0` for true, `1` for false, or a different
  number for an error.
  - Examples: the `test` builtin, and the `grep` command.

Oil's error handling constructs must deal with this fundamental inconsistency.

### The Disabled `errexit` Pitfall (`if myfunc`)

Here's an example of a bad interaction between the `if` statement, shell
functions, and `errexit`.  It's a **mistake** in the design of the shell
language.

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

1. Are we trying to test success/failure or true/false?
2. `if` tests a single exit status, but every command in a function has an exit
   status.  Which one should it look at?

This quirk occurs in all "conditional" contexts:

1. The condition of the `if`, `while`, and `until`  constructs
2. A command/pipeline prefixed by `!` (negation)
3. Every clause in `||` and `&&` except the last.

We can't fix this decades-old bug in shell.  Instead we disallow dangerous code
with `strict_errexit`, and add new error handling mechanisms.

## Oil Error Handling: The Big Picture 

We've reviewed how POSIX shell and bash work, and showed fundamental problems
with the shell language.

But when you're using Oil, you don't have to worry about any of this!

### Oil Fails On Every Error

This means you don't have to explicitly check for errors.  Examples:

    shopt --set oil:basic       # Enable good error handling in bin/osh
                                # It's the default in bin/oil.
    shopt --set strict_errexit  # Disallow bad shell error handling.
                                # Also the default in bin/oil.

    local date=$(date X)        # 'date' failure is fatal
    # => date: invalid date 'X' 

    echo $(date X)              # ditto

    echo $(date X) $(ls > F)    # 'ls' isn't executed; 'date' fails first

    ls /bad | wc                # failure of 'ls' is fatal

    diff <(sort A) <(sort B)    # failure of 'sort' is fatal

On the other hand, you won't experience this problem caused by `pipefail`:

    yes | head                 # doesn't fail due to SIGPIPE

The details are explained below.

### Handle Errors With `try`

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

Note that `_status` is different than `$?`, and that idiomatic Oil programs
don't look at `$?`.

You can omit `{ }` when invoking a single command.  Here's how to invoke a
function without the *disabled `errexit` pitfall*:

    try myfunc            # Unlike 'myfunc', doesn't abort on error
    if (_status !== 0) {
      echo 'failed'
    }

Exceptions while evaluating expressions are turned into "command" exit codes,
which can be examined the same way:

    var d = {}                     # empty dict
    try {
      setvar x = d['nonexistent']  # exception: missing key
      var y = 42 / 0               # exception: divide by zero
    }
    if (_status !== 0) {
      echo 'expression error'
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


See [Oil vs. Shell Idioms > Error Handling](idioms.html#error-handling) for
more examples.

### `boolstatus` Enforces 0 or 1 Status

The `boolstatus` builtin helps with the *True / False / Error* problem:

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

## Reference: Global Options

**Most users can skip the rest of this doc.**  You don't need to know all the
details to use Oil.

Under the hood, we implement the `errexit` option from POSIX, bash options like
`pipefail` and `inherit_errexit`, and add more options of our
own.  They're all hidden behind [option groups](options.html) `oil:basic` and
`oil:all`.

The following sections explain Oil's new options.

### `command_sub_errexit` Adds More Errors

In all Bourne shells, the status of command subs is lost, so errors are ignored
(details in the [appendix](#quirky-behavior-of)).  For example:

    echo $(date X) $(date Y)  # 2 failures, both ignored
    echo                      # program continues

The `command_sub_errexit` option makes this an error.  The status `$?` of the
parent `echo` command will be `1`, so if `errexit` is on, the shell will abort.

(Other shells should implement `command_sub_errexit`!)

### `process_sub_fail` Is Analogous to `pipefail`

Similarly, in this example, `sort` will fail if the file doesn't exist.

    diff <(sort left.txt) <(sort right.txt)  # any failures are ignored

But there's no way to see this error in bash.  Oil adds `process_sub_fail`,
which folds the failure into `$?` so `errexit` can do its job.

You can also inspect the special `_process_sub_status` array variable with
custom error logic.

### `strict_errexit` Flags Two Problems

Like other `strict_*` options, Oil's `strict_errexit` improves your shell
programs, even if you run them under another shell like [bash]($xref)!  It's
like a linter *at runtime*, so it can catch things that [ShellCheck][] can't.

[ShellCheck]: https://www.shellcheck.net/

`strict_errexit` disallows code that exhibits these problems:

1. The *disabled `errexit` pitfall*, which I showed above.  I also think of it as
   the `if myfunc` pitfall.
1. The `local x=$(false)` pitfall.  The exit code of `false` is lost, for
   reasons described in the appendix.

There's also a "meta" problem where disallowing bad code in child processes run
from conditionals is impossible!  If the child fails with an **error**, the
parent `if` might confuse it for **false**.  (See this `if myfunc | grep`
example in [Oil vs. Shell Idioms > Does a Pipeline
Succeed?](idioms.html#does-a-pipeline-succeed))

So `strict_errexit` is quite strict, but it leads to clear and simple code.

#### Rules to Prevent the Disabled `errexit` Pitfall

In any conditional context, `strict_errexit` disallows:

1. All commands except `((`, `[[`, and some simple commands (e.g. `echo foo`).
   - Detail: `! ls` is considered a pipeline in the shell grammar.  We have to
     allow it, while disallowing `find | grep foo`.
2. Function/proc invocations (which are a special case of simple
   commands.)
3. Command sub and process sub (`shopt --unset allow_csub_psub`)

This means that you should check the exit status of functions differently.

No:

    if ! myfunc; then  # function calls in conditionals are disallowed
      echo 'failed'
    fi

Yes:

    try myfunc
    if (_status !== 0) {
      echo 'failed'
    }

#### Rule to Prevent the `local x=$(false)` Pitfall

- Command Subs and process subs are disallowed in assignment builtins (`local`,
  `declare`, `readonly`, `export`)

No:

    local x=$(false)

Yes:

    var x = $(false)   # Oil style

    local x            # Shell style
    x=$(false)

### `sigpipe_status_ok` Ignores an Issue With `pipefail`

When you turn on `pipefail`, you may inadvertently run into this behavior:

    yes | head
    # => y
    # ...

    echo ${PIPESTATUS[@]}
    # => 141 0

That is, the `yes` command **fails** with `SIGPIPE` status `141` because `head`
closed the pipe it was writing to.

This error shouldn't be fatal, so Oil has a `sigpipe_status_ok` option, which
is on unless you're using OSH.

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

Why is `strict_errexit` a different option than `command_sub_errexit`?

</div>

Because `shopt --set strict:all` can be used to improve scripts that are run
under other shells like [bash]($xref).  It's like a runtime linter that
disallows dangerous constructs.

On the other hand, if you write code with `command_sub_errexit` on, it's
impossible to get the same failures under bash.  So `command_sub_errexit` is
not a `strict_*` option, and it's meant for OSH-only / Oil-only code.

## Reference: Exit Status of Oil "Commands"

Each "command" in the shell grammar has a rule for its exit status.  Here are
the rules for Oil's new command types:

- `proc`.  As with defining shell functions, defining a `proc` never fails.  It
  always exits `0`.
- `var`, `const`, `setvar`, and the `_` keyword.  If an exception occurs during
  expression evaluation, the status is `3`.  Otherwise it's `0`.

Similarly, an expression sub like like `echo $[1 / 0]` will raise an internal
exception, and the status of `echo` will be `3`.  (This is similar to what
happens when a redirect fails.)

Note: The status `3` is an arbitrary non-zero status that's not used by other
shells.  Status `2` is generally for syntax errors and status `1` is for most
runtime failures.
  
## Summary

Oil uses three mechanisms to fix error handling once and for all.

It has two new **builtins** that relate to errors:

1. `try` lets you explicitly handle errors when `errexit` is on.
1. `boolstatus` enforces a true/false meaning.  (This builtin is less common).

It has three **special variables**:

1. The `_status` integer, which is set by `try`.
   - Remember that it's distinct from `$?`, and that idiomatic Oil programs
     don't use `$?`.
1. The `_pipeline_status` array (another name for bash's `PIPESTATUS`)
1. The `_process_sub_status` array for process substitutions.

Finally, it supports all of these **global options**:

- From POSIX shell:
  - `errexit`
- From [bash]($xref):
  - `pipefail`
  - `inherit_errexit`
- New:
  - `command_sub_errexit` allows failure in the middle of commands.
  - `process_sub_fail` is analogous to `pipefail`.
  - `strict_errexit` flags two common problems.
  - `sigpipe_status_ok` ignores a spurious failure.
  - `verbose_errexit` controls whether error messages are printed.

When using `bin/osh`, set all options at once with `shopt --set oil:basic`.  Or
use `bin/oil`, where they're set by default.

<!--
Related 2020 blog post [Reliable Error
Handling](https://www.oilshell.org/blog/2020/10/osh-features.html#reliable-error-handling).
-->


## Related Docs

- [Oil vs. Shell Idioms](idioms.html) shows more examples of `try` and `boolstatus`.
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
- [Egg Expressions (Oil Regexes)](eggex.html)

For reference, this work on error handling was described in [Four Features That
Justify a New Unix
Shell](https://www.oilshell.org/blog/2020/10/osh-features.html) (October 2020).
Since then, we changed `try` and `_status` to be more powerful and general.

## Appendices

### List Of Pitfalls

We showed examples of these pitfalls above:

1. The *disabled `errexit` pitfall*, aka the `if myfunc` Pitfall.  (`strict_errexit`)
2. The `local x=$(false)` Pitfall (`strict_errexit`)
3. The `yes | head` Pitfall. (`sigpipe_status_ok`)

Here are more error handling pitfalls don't require changes to Oil:

4. The Trailing `&&` Pitfall
   - When `test -d /bin && echo found` is at the end of a function, the exit
     code is surprising.
   - Solution: always use `if` rather than `&&`.
   - More reasons: the `if` is easier to read, and `&&` isn't useful when
     `errexit` is on.
5. The surprising return value of `(( i++ ))`, `let`, `expr`, etc.
   - Solution: Use `i=$((i + 1))`, which is valid POSIX shell.
   - In Oil, use `setvar i += 1`.

#### 6. In bash, `errexit` is disabled in command subs (`inherit_errexit`)

Example:

    set -e
    shopt -s inherit_errexit  # needed to avoid 'touch two'
    echo $(touch one; false; touch two)

#### 7. Bash has a grammatical quirk with `set -o failglob`

Like the definition of `$?`, this is a quirk that relates to the shell's
**grammar**.  Consider this program:

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

### Quirky Behavior of `$?`

Simple commands have an obvious behavior:

    echo hi           # $? is 0
    false             # $? is 1

This is the problem that `command_sub_errexit` fixes:

    echo $(false)     # we lost the exit code of false, so $? is 0

Surprisingly, bare assignments take on the value of any command subs:

    x=$(false)        # we did NOT lose the exit code, so $? is 1

But assignment builtins have the problem again:

    local x=$(false)  # exit code is clobbered, so $? is 0

So shell is confusing and inconsistent, but Oil fixes all these problems.  You
never lose the exit code of `false`.



