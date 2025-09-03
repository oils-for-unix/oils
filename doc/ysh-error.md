---
default_highlighter: oils-sh
---

Guide to YSH Error Handling
===========================

There are just a few concepts to know:

- [error][] builtin - "Throw" an error, with a custom message, error code, and
  other properties.
- [try][] builtin - Run a block, and set the [_error][] register to a `Dict`.
  - `_error.code` will be `0` on success, or non-zero if an error is thrown in
    the block.
- [failed][] builtin - A handy shortcut to test for a non-zero error code.

[try]: ref/chap-builtin-cmd.html#try
[_error]: ref/chap-special-var.html#_error

[error]: ref/chap-builtin-cmd.html#error
[failed]: ref/chap-builtin-cmd.html#failed

<div id="toc">
</div>

## Examples

### Handle command and expression errors with `try`

Here's the most basic form:

    try {
      ls /zz
    }
    if (_error.code !== 0) {
      echo "ls failed with $[_error.code]"
    } 
    # => ls failed with error 2


### The `failed` builtin is a shortcut

Instead of writing `if (_error.code !== 0)`, you can write `if failed`:

    if failed {
      echo "ls failed with $[_error.code]"
    } 

This saves you 7 punctuation characters: `( _ . !== )`

### Use a `case` statement if it's not just pass/fail

Sometimes it's nicer to use `case` rather than `if`:

    try {
      grep '[0-9]+' foo.txt
    }
    case (_error.code) {
      (0)    { echo 'found' }
      (1)    { echo 'not found' }
      (else) { echo 'error invoking grep' }
    }

### Error may have more attributes, like `_error.message`

    try {
      var x = fromJson('{')
    }
    if failed {
      echo "JSON failure: $[_error.message]"
    }
    # => JSON failure: expected string, got EOF

### The `error` builtin throws custom errors

A non-zero exit code results in a simple shell-style error:

    proc simple-failure {
      return 2
    }

    try {
      simple-failure
    }
    echo "status is $[_error.code]"
    # => status is 2

The `error` builtin is more informative:

    proc better-failure {
      error 'Custom message' (code=99, foo='zz')
    }

    try {
      better-failure
    }
    echo "$[_error.code] $[_error.message] foo=$[_error.foo]"
    # => 99 Custom message foo=zz"

## Tips

### Proc Return Status Should Be Either OK-Fail, or True-False-Fail

<style>
table {
  margin-left: 2em;
  background-color: #eee;
}
thead {
  background-color: white;
}
</style>

That is, use **one** of these styles:

<div style="display: flex; gap: 20px;">
<table cellpadding="10" cellspacing="5">

- thead
  - Return Status
  - Meaning
- tr
  - 0
  - OK
- tr
  - 1 or more
  - Fail

</table>

<table cellpadding="10" cellspacing="5">

- thead
  - Return Status
  - Meaning
- tr
  - 0
  - True
- tr
  - 1
  - False
- tr
  - 2 or more
  - Fail

</table>
</div>

For example, here's a proc that does is **not** follow the style:

    proc is-different (left, right) {
      mkdir /tmp/dest            # may return 1 on failure

      cp $left $right /tmp/dest  # may return 1 on failure

      diff -u $left $right       # 0-true, 1-false, 2-failure
    }

The exit code isn't well-defined, because `mkdir` and `cp` use the OK-fail
paradigm, while `diff` uses the **boolean** paradigm:

Explicitly checking for failure fixes it:

    proc different (left, right) {
      if ! mkdir /tmp/dest {
        return 2                 # 2-failure
      }
      if ! cp $left $right /tmp/dest {
        return 2                 # 2-failure
      }

      diff -u $left $right       # 0-true, 1-false, 2-failure
    }

## Related

- [YSH vs. Shell Idioms > Error Handling](idioms.html#error-handling)
- [YSH Fixes Shell's Error Handling (`errexit`)](error-handling.html) - A
  detailed design doc


