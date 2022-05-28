---
in_progress: true
default_highlighter: oil-sh
---

Exit Codes
==========

The meaning of exit codes is a convention, and generally follows one of two
paradigms.

See [Oil Fixes Shell's Error Handling](../error-handling.html) for more detail.

<div id="toc">
</div>

## The Success / Failure Paradigm 

- `0` for **success**.
- `1` for **runtime error**
  - Example: `echo foo > out.txt` and `out.txt` can't be opened.
  - Example: `fg` and there's not job to put in the foreground.
- `2` for **parse error**.  This means that we didn't *attempt* to do
  anything, rather than doing something, then it fails.
  - Example: A language parse error, like `echo $(`.
  - Example: Builtin usage error, like `read -z`.
- `3` for runtime **expression errors**.  The expression language is new to
  Oil, so its errors have a new exit code.
  - Example: divide by zero `42 / 0` 
  - Example: index out of range `a[1000]`

POSIX exit codes:

- `126` for permission denied when running a command (`errno EACCES`)
- `127` for command not found

Hint. Error checking often looks like this:

    try ls /bad
    if (_status !== 0) {
      echo 'failed'
    }

## The Boolean Paradigm

- `0` for **true**
- `1` for **false**.
  - Example: `test -f foo` and `foo` isn't a file.
- `2` for **error** (usage error, parse error, etc.)
  - Example: `test -q`: the flag isn't accepted.

Hint. The `boolstatus` builtin ensures that false and error aren't confused:

    if boolstatus test -f foo {
      echo 'foo exists'
    }
