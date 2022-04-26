---
in_progress: yes
default_highlighter: oil-sh
---

Oil Fixes Shell's Error Handling (`errexit`)
============================================

Synopsis:

- POSIX shell has **fundamental** problems with error handling.  With `set -e`
  (`errexit`), you're *damned if you do and damned if you don't*.
- GNU [bash]($xref) fixes some of those problems, but **adds its own**, e.g.
  related to command subs, process subs, and assignment builtins.
- Oil **fixes all of the problems** by adding new global options, builtins, and
  special variables.  They are largely hidden behind a nice new interface, e.g.
  `try` and `_status`.

If you disagree with this claim, file a bug.  In particular:

- Oil never silently ignores an error.  That is, it never loses an exit code
  (unlke shell).
- There's never a reason to write an Oil script without `set -e`, which is on
  by default.

This document explains how Oil makes these guarantees.  We first review shell error
handling, and then show idiomatic Oil code.  Finally, we explain the details
that make it possible.

<div id="toc">
</div>

## Review of Shell Error Handling Mechanisms

### POSIX Shell

- The special variable `$?` is the "last exit status".
- If you `set -e` (aka `set -o errexit`), then the shell will abort if `$?` is nonzero.
  - The is subject to the "Disabled `errexit` Quirk", which I describe below.

A big caveat (language design bug) is that `$?` and `set -e` work on the basis
of grammatical **commands**, which causes the pitfalls explained below.

### Bash

- `set -o pipefail`
- `${PIPESTATUS[@]}` so you have access to the exit codes from all processes in a pipeline.
- `shopt -s inherit_errexit` to fix a bash-specific bug with command subs.

There are still bugs.

## Fundamental Problems With The Language

There are many details.  But these are fundamental issues.

### `$?` Is Tied to Top-Level "Commands"

The POSIX shell grammar has a "command" rule.

For example, this is actually a single command with a single exit status:

    local x=$(date %d)    

So is the conditional of `if` or `while`:

    if myfunc; then
      echo 'success'
    fi

Pipelines, command subs, process subs all have issues.  See Appendix.

### `$?` Is Overloaded: OK-Error or True-False?

`grep`.


### The "Disabled `errexit` Quirk" 

In Conditional Contexts

TODO: This is important to understand.

Here's some background for understanding the additional `errexit` options
described below.

In all Unix shells, the `errexit` check is disabled in these situations:
 
1. The condition of the `if`, `while`, and `until`  constructs
2. A command/pipeline prefixed by `!`
3. Every clause in `||` and `&&` except the last.

Now consider this situation:

1. `errexit` is **on**
2. The shell disables it one of those three situations
3. While disabled, the user touches it with `set -o errexit` (or `+o` to turn
   it off).

Surprising behavior: Unix shells **ignore** the `set` builtin for awhile,
delaying its execution until **after** the temporary disablement.


## Oil Error Handling: The Big Picture 

You don't have to worry about all this stuff. Here is "The User Interface".

### Oil Fails On Every Error

In other words, It doesn't lose an exit status.

Normal Code Doesn't check errors.

    shopt --set oil:basic  # or use bin/oil

    echo $(date %d)   # failure of 'date' is fatal

    ls /bad | wc      # failure of 'ls' is fatal

    yes | head        # no SIGPIPE problem

### You Can Check Errors With `try`, Then Inspect `_status`

Sometimes you want to check errors.

Proc:

    try myfunc /bad
    if (_status !== 0) {
      echo 'failed'
    }

Two Commands:

    try {
      ls /bin
      ls /bad
    }
    if (_status !== 0) {
      echo 'failed'
    }


Pipeline:

    try {
      ls /bad | wc
    }
    write -- @_pipeline_status

Process Sub:

    try {
      diff <(sort left.txt) <(sort right.txt)
    }
    write -- @_process_sub_status

### `boolstatus`

## Reference: Global Options

You don't have to know all this stuff!

TODO: link to global options doc.

### `command_sub_errexit` Adds Errors Not Available In Other Shells

- `command_sub_errexit`: Check more often for non-zero status.  In particular, the
  failure of a command sub can abort the entire script.  For example, `local
  foo=$(false)` is a fatal runtime error rather than a silent success.


When both `inherit_errexit` and `command_sub_errexit` are on, this code

    echo 0; echo $(touch one; false; touch two); echo 3

will print `0` and touch the file `one`.

1. The command sub aborts at `false` (`inherit_errexit`), and
2. The parent process aborts after the command sub fails (`command_sub_errexit`).


### `process_sub_fail` Allows More Failure

Needed so that pipefail works.

### `strict_errexit` Disallows Two Pitfalls

1. It disallows any commands except simple commands, `((`, and `[[`.
	 - Detail: '! false' is technically a pipeline and we have to allow
     it, while disallowing 'ls | wc'.
2. It disallows proc invocations (which are a special case of simple commands.)
3. It disallows command sub and process sub (`shopt --unset allow_csub_psub`)

Under `strict_errexit`

No:

    if myfunc; then       # disallowed by strict_errexit
      echo 'success'
    fi

Yes:

    try myfunc            # doesn't abort
    if (_status === 0) {
      echo 'success'
    }

No:

    local d=$(date %d)
    d=$(date %d)

Yes:

    var x = $(date %d)
    setvar x = $(date %d)

- `strict_errexit` makes the quirk above irrelevant.  Compound commands,
  including **functions**, can't be used in any of those three situations.  You
  can write `set -o errexit || true`, but not `{ set -o errexit; false } ||
  true`.  When this option is set, you get a runtime error indicating that you
  should **change your code**.  Consider using the ["at-splice
  pattern"][at-splice] to fix this, e.g. `$0 myfunc || echo errexit`.

Note: it's also stricter than you think because of what I cal the "Conditional
- Child Process" problem.  We want to flag a problem in your code, but that's
impossible in a conditional because success/failure is conflated with
true/false.  So we have to disallow more things at the top level.

That's why the idiom is

    try ls /bad
    if (status != 0) {
      echo 'failed'
    }

Rather than something like:

    if ! old-try-builtin ls  /bad {
      echo 'failed'
    }

### `sigpipe_status_ok` Ignores A Common Issue

Related to `pipeefail`.

### More

- `verbose_errexit`.  TODO: Do we need this?

## Reference: Exit Status of New Language Constructs

- `var`, `const`, `setvar`.
  - `1` if an exception occured, or `0` otherwise.
- The `_` keyword behaves the same way.

## Summary

TODO: Transcribe [Reliable Error
Handling](//www.oilshell.org/blog/2020/10/osh-features.html#reliable-error-handling).

Builtins (TODO)

- The `try` builtin, which will take a block
- The `boolstatus` builtin, for `grep`

Special variables

- `_pipeline_status` is an alias for `PIPESTATUS`
- `_process_sub_status` is analogous, for `<(sort left.txt)`
- `_status`, which is set by `try`

More shell options:

- `process_sub_fail` is analogous to `pipefail`.
- `command_sub_errexit`
- `strict_errexit`
- `sigpipe_status_ok` -- for `yes | head`
- Set them all with `shopt --set oil:basic`, or use `bin/oil`.

### Related Documents

- [Shell Idioms](shell-idioms.html).  There's a section  on fixing
  `strict_errexit` problems.

Good articles on `errexit`:

- <http://mywiki.wooledge.org/BashFAQ/105>
- <http://fvue.nl/wiki/Bash:_Error_handling>

Spec Test Suites:

- <https://www.oilshell.org/release/latest/test/spec.wwz/survey/errexit.html>
- <https://www.oilshell.org/release/latest/test/spec.wwz/survey/errexit-oil.html>

## Appendix: Examples Of Pitfalls

### The `if myfunc` Pitfall (`strict_errexit`)

TODO: show transcript

### The `local x=$(false)` Pitfall (`strict_errexit`)

TODO: show transcript

Background: In shell, `local` is a builtin rather than a keyword, which means
`local foo=$(false)` behaves differently than than `foo=$(false)`.

### The `pipefail SIGPIPE` Pitfall (`sigpipe_status_ok`)

An extra error where you didn't expect it.

### More Pitfalls

- The Trailing `&&` pitfall
  - `test -d /bin && echo found`
  - Solution: just use `if`.  Don't use `&&` for chaining in Oil.  Because
    `errexit` is on by default.
- Return value of bash `(( i++ ))`, `let`, `expr`, and so forth
  - Solution: Always use `i=$((i + 1))`.  This also has the advantage of being POSIX.
  - In Oil, `setvar i += 1` is preferred.


## Appendix: Shell Behavior

Here's some background knowledge on Unix shell, which will motivate the
improvements in Oil.

(1) Shell has a global variable `$?` that stores the integer status of the last
command.  For example:

- the builtin `echo hi` returns `0`
- `ls /zzz` will return an error like `2`
- `nonexistent-command` returns `127`

(2) "Bare" Assignments are considered commands.

- The exit status of `a=b` is `0`.
- The exit status of `a=$(false)` is `1`, because `false` returned 1.

(3) Assignment builtins have their own exit status.

Surprisingly, the exit status of `local a=$(false)` is `0`, not `1`.  That is,
simply adding `local` changes the exit status of an assignment.

The `local` builtin has its own status which overwrites `$?`, and you lose the
status of `false`.

(4) You can explicitly check `$?` for failure, e.g. `test $? -eq 0 || die
"fail"`.

The `set -e` / `set -o errexit` mechanism tries to automate these checks, but
it does it in a surprising way.

This rule causes a lot of problems:

> The -e setting shall be ignored when executing the compound list following
> the while, until, if, or elif reserved word, a pipeline beginning with the !
> reserved word, or any command of an AND-OR list other than the last.

(5) Bash implement `errexit` differently than other shells.  `shopt -s More details:

- The implements `errexit` differently.
- The status of a pipeline is the status of its last component.  For example,
  after `ls | grep foo`, the variable `$?` is set to the exit status of `grep`.
  - If `set -o pipefail`, then the status of a pipeline is the maximum of any
    status.

## Idioms (TODO:move)

TODO: Maybe move to `idioms`.md`

### Handle Error Explicitly

Oil

    try {
      my-complex-func
    }
    echo $_status

There's no way to do this in shell!

Shell

    set +o errexit

    my-complex-func
    status=$?

    set -o errexit

### Ignore Error

Shell:

    ls /bad || true   # this is OK


Oil:

    try ls /bad


### Style Guide (TODO: move)

No:

    if myfunc ...             # internal exit codes would be thrown away

    if ls | wc -l ;           # first exit code would be thrown away


Yes:

    if external-command ...   # e.g. grep
    if builtin ...            # e.g. test
    if $0 myfunc ...          # $0 pattern

The `$0 myfunc` pattern wraps the function in an external command.

<!-- TODO: link to blog post explaining it -->

