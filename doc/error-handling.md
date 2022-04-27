---
in_progress: yes
default_highlighter: oil-sh
---

Oil Fixes Shell's Error Handling (`errexit`)
============================================

Synopsis:

- POSIX shell has **fundamental** problems with error handling.  With `set -e`
  aka `errexit`, you're *damned if you do and damned if you don't*.
- GNU [bash]($xref) fixes some of those problems, but **adds its own**, e.g.
  related to process subs, command subs, and assignment builtins.
- Oil **fixes all the problems** by adding new global options, builtins, and
  special variables.  They are largely hidden behind a nice new interface, e.g.
  `try` and `_status`.

If you find a hole in this claim, please [file a bug][].  More specifically:

- Oil never silently ignores an error.  Unlike shell, it never loses an exit
  code.
- There's never a reason to write an Oil script without `set -e`, which is on
  by default.

This document explains how Oil makes these guarantees.  We first review shell error
handling, and then show idiomatic Oil code.  Finally, we look under the hood at
the underlying mechanisms.

[file a bug]: https://github.com/oilshell/oil/issues

<div id="toc">
</div>

## Review of Shell Error Handling Mechanisms

### POSIX Shell

- The special variable `$?` is the exit status of the last "command".
- If `errexit` is enabled, then the shell will abort if `$?` is nonzero.
  - This is subject to the "Disabled `errexit` Quirk", which I describe below.

These mechanisms are fundamentally incomplete.

### Bash

Bash is better about handling the failure of pipelines like `ls /nonexistent |
wc`.

- The `${PIPESTATUS[@]}` variable has the exit codes of all processes in a
  pipeline.
- When `set -o pipefail` is enabled, `$?` takes into account all processes in a
  pipeline.  Without this setting, the failure of `ls` would be ignored.
- `shopt -s inherit_errexit` fixes a bash-specific bug with command subs.

But there are many other places where bash will lose an exit code.

## Fundamental Problems With The Language

Shell error handling is complex, but here are 3 fundamental issues you should
remember.

### `$?` Doesn't Correspond to Commands or Processes

Each process and shell builtin has an exit status.  But the definition of `$?`
is obscure: it's tied to the `command` rule in the POSIX shell grammar, which
does **not** correspond to a single process with an exit status.

We saw that `pipefail` fixes one case:

    ls /nonexistent | wc   # 2 proceses, 2 exit codes, but just one $?

But there are others:

    local x=$(false)                 # 2 exit codes, but just one $?
    diff <(sort left) <(sort right)  # 3 exit codes, but just one $?

### What Does `$?` Mean?  It's Overloaded

- **OK or Error**. Tools like `cp` return `0` for success and non-zero for
  failure.
- **True, False, or Error**. Builtins like `test` and commands like `grep`
  return `0` for true, `1` for false, or a number greater than `2` for an
  error.

Oil's error handling constructs must accomodate this fundamental confusion.

### The "Disabled `errexit` Quirk" 

Here's an example an **important bug** in the design of the shell language:

    set -o errexit     # don't ignore errors

    myfunc() {
      ls /bad          # fails with status 1
      echo 'should not get here'
    }

    # Correct: script fails before echo
    myfunc
    # => ls: '/bad': no such file or directory

    # Surprise!
    if myfunc; then
      echo OK
    fi
    # => ls: '/bad': no such file or directory
    # => should not get here

We see the message because the shell **silently disables** `errexit` while
executing the condition of `if`.  The fundamental problems we mentioned that
cause this:

1. It's unclear whether you are testing for success/failure or true/false.
2. `if` tests a single exit status, but every statement in a function has an
   exit status.  Which one do you use?

This quirk occurs in all "conditional" contexts:

1. The condition of the `if`, `while`, and `until`  constructs
2. A command/pipeline prefixed by `!` (negation)
3. Every clause in `||` and `&&` except the last.

## Oil Error Handling: The Big Picture 

We've reviewed how POSIX shell and bash work, and reviewed fundamental problems
with the shell language.

But when you're using Oil, you don't have to worry about all this.

### Oil Fails On Every Error

You don't have to explicitly check errors, and errors won't be ignored.
Examples:

    shopt --set oil:basic     # Enable good error handling in bin/osh
                              # It's the default in bin/oil.

    local date=$(date %d)     # 'date' failure is fatal

    echo $(date %d)           # ditto

    echo $(date %d) $(ls > F) # 'date' fails before execution of 'ls'

    ls /bad | wc              # failure of 'ls' is fatal

    diff <(sort A) <(sort B)  # failure of 'sort' is fatal

On the other hand, you won't experience this problem caused by `pipefail`:

    yes | head                # doesn't fail due to SIGPIPE

The details are explained below.

### Handle Errors With `try`

You may want to **handle failure** instead of aborting the shell.  In this
case, use the `try` builtin, and inspect the `_status` variable it sets.

    try {                 # try takes a block of commands
      ls /lib
      ls /bad             # stops at first failure
      ls /bin
    }                     # After try, $? is always 0
    if (_status !== 0) {
      echo 'failed'
    }

Note that `_status` is different than `$?`, and idiomatic Oil programs don't
look at `$?`.

You can omit `{ }` when invoking a single command.  Here's how to invoke a
function without the *Disabled `errexit` Quirk*:

    try myfunc            # Unlike 'myfunc', doesn't abort on error
    if (_status !== 0) {
      echo 'failed'
    }

Fatal errors in expressions are turned into exit codes, which can be examined with try:

    try {
      var d = {}
      setvar x = d['nonexistent']  # exception: missing key
      var y = 42 / 0               # exception: divide by zero
    }
    if (_status !== 0) {
      echo 'error'
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

### `boolstatus` Enforces 0 or 1 Status

The `boolstatus` builtin helps with the *True, False, or Error* problem:

    if boolstatus grep PATTERN FILE.txt {
      echo 'found'      # status 0 means 'found'
    } else {
      echo 'not found'  # status 1 means 'not found'
    }

Rather than confusing **error** with **false**, `boolstatus` will abort the
program if `grep` doesn't return 0 or 1.

<!--
There are some tools like `grep` that return a boolean status:

- `0` means true (pattern found)
- `1` means false (pattern not found)
- Other statuses indicate an error, like `2` for a syntax error in the pattern.

But the `if` statement tests for zero or non-zero status.  An **error** could
be confused with a logical **false**.

The `boolstatus` builtin addresses this issue.  If the status isn't `0` or `1`,
it aborts the whole program:
-->

## Reference: Global Options

You **don't** need to read the rest of this doc to use Oil.

But some users may be curious about the many mechanisms under the hood.  We
implement the `errexit` option from POSIX, bash options like `pipefail` and
`inherit_errexit`, and add [more options of our own](options.html).

They're all hidden behind `oil:basic` (or `bin/oil`).

### `command_sub_errexit` Adds Errors Not Available In Other Shells

- `command_sub_errexit`: Check more often for non-zero status.  In particular, the
  failure of a command sub can abort the entire script.  For example, `local
  foo=$(false)` is a fatal runtime error rather than a silent success.


When both `inherit_errexit` and `command_sub_errexit` are on, this code

    echo 0; echo $(touch one; false; touch two); echo 3

will print `0` and touch the file `one`.

1. The command sub aborts at `false` (`inherit_errexit`), and
2. The parent process aborts after the command sub fails (`command_sub_errexit`).


### `process_sub_fail` Is Analogous to `pipefail`

Needed so that `errexit` works.

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

### `sigpipe_status_ok` Ignores an Issue With `pipefail`

Related to `pipefail`.

### More

- `verbose_errexit` controls whether

## Reference: Exit Status of New Language Constructs

Each "command" in the shell grammar has a rule for its exit status.  Oil adds
new types of grammatical commands:

- `var`, `const`, `setvar`, and the `_` keyword.  Their status is `1` if an
  exception occured, or `0` otherwise.
- An expression sub like like `echo $[1 / 0]` will raise an internal exception,
  which causes the command to fail with status 1.
  
TODO: implement these rules.  Maybe consider status 3?

## Summary

Oil's has two new **builtins** that relate to errors:

1. `try` lets you explicitly handle errors when `errexit` is on.
1. The less common `boolstatus` enforces a true/false meaning.

And 3 **special variables**:

1. The `_status` integer, which is set by `try`.
   - Remember that it's distinct from `$?`, and idiomatic Oil programs don't use
     `$?`.
1. The `_pipeline_status` array (an alias for bash's `PIPESTATUS`)
1. The `_process_sub_status` array for process substitutions.

Oil supports all of these **global options**:

- From POSIX shell:
  - `errexit`
- From [bash]($xref):
  - `pipefail`, `inherit_errexit`
- New:
  - `process_sub_fail` is analogous to `pipefail`.
  - `command_sub_errexit` allows failure in the middle of commands.
  - `strict_errexit` prevents 2 common pitfalls.
  - `sigpipe_status_ok` ignores a spurious failure.
  - `verbose_errexit` controls whether error messages are printed.

When using `bin/osh`, set them all with `shopt --set oil:basic`.  Or use
`bin/oil`, where they are on by default.

<!--
Related 2020 blog post [Reliable Error
Handling](https://www.oilshell.org/blog/2020/10/osh-features.html#reliable-error-handling).
-->


### Related Documents

- [Oil vs. Shell Idioms](idioms.html) shows more examples of `try` and `boolstatus`.
- [Shell Idioms](shell-idioms.html) has a section  on fixing `strict_errexit`
  problems.

Good articles on `errexit`:

- <http://mywiki.wooledge.org/BashFAQ/105>
- <http://fvue.nl/wiki/Bash:_Error_handling>

Spec Test Suites:

- <https://www.oilshell.org/release/latest/test/spec.wwz/survey/errexit.html>
- <https://www.oilshell.org/release/latest/test/spec.wwz/survey/errexit-oil.html>

## Appendix: Examples Of Pitfalls

#### The `if myfunc` Pitfall (`strict_errexit`)

TODO: show transcript

#### The `local x=$(false)` Pitfall (`strict_errexit`)

TODO: show transcript

Background: In shell, `local` is a builtin rather than a keyword, which means
`local foo=$(false)` behaves differently than than `foo=$(false)`.

#### The `pipefail SIGPIPE` Pitfall (`sigpipe_status_ok`)

An extra error where you didn't expect it.

#### Another Grammatical Quirk

`set -o failglob` depends on `;` or newline.

#### More Pitfalls

- The Trailing `&&` pitfall
  - `test -d /bin && echo found`
  - Solution: just use `if`.  Don't use `&&` for chaining in Oil.  Because
    `errexit` is on by default.
- Return value of bash `(( i++ ))`, `let`, `expr`, and so forth
  - Solution: Always use `i=$((i + 1))`.  This also has the advantage of being POSIX.
  - In Oil, `setvar i += 1` is preferred.

## Appendix: Shell Execution Model

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

