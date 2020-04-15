---
in_progress: yes
---

set -e / errexit in shell
=========================

Unix shell experts are divided on what the best way to handle errors is.  
Existing mechanisms like `set -e` are unreliable, and shell scripts are often
flaky as a result.

The goal of Oil is:

> Don't give anyone an excuse not to use `set -e`

And this doc explains how.


Remember that `bin/osh` behaves exactly like a POSIX shell, so all your
existing scripts will continue to work, with their quirky error handling.

`bin/oil` has `errexit` on, so you don't need to write it explicitly.  It also
has a bunch of options to fix the quirky behavior, including:

- `strict_errexit`: Disallow surprising / dangerous programming patterns.  It
  will alert you when POSIX shell interpreters would do something surprising.
- `more_errexit`: Fail more often.
- `inherit_errexit` (bash 4.4 also has this)


<div id="toc">
</div>

<!-- TODO: copy section from OSH manual -->

## Background

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

## The Fundmental Problem

- success/fail of a command and logical true/false are conflated in shell.
- Oil has commands and expressions.  Commands have a status but expressions
  don't.

- TODO:
  - grep
  - test
  - command -v



## Problem

### Solution in Shell

    set +o errexit

    my-complex-func
    status=$?

    other-func
    status=$?

    set -o errexit


### Solution Oil

    shopt -u errexit {
      var status = 0 

      my-complex-func
      setvar status = $?

      other-func
      setvar status = $?
    }

## Style Guide

No:

    if myfunc ...             # internal exit codes would be thrown away

    if ls | wc -l ;           # first exit code would be thrown away


Yes:

    if external-command ...   # e.g. grep
    if builtin ...            # e.g. test
    if $0 myfunc ...          # $0 pattern


The `$0 myfunc` pattern wraps the function in an external command.

<!-- TODO: link to blog post explaining it -->

### Links


- Spec Test Suites:
  - <https://www.oilshell.org/release/latest/test/spec.wwz/errexit.html>
  - <https://www.oilshell.org/release/latest/test/spec.wwz/errexit-oil.html>
