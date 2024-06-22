---
default_highlighter: oils-sh
---

YSH Error Handling: A Quick Guide
=================================

There are just a few concepts to know:

- [try][] - Run a block, and set the `_error` register to a `Dict`.
  - `_error.code` will be `0` on success, or non-zero on failure.
- [error][] - "Throw" an error, with a custom message, error code, and other
  properties.
- [failed][] - Handy shortcut that tests for non-zero error code.

[error]: ref/chap-builtin-cmd.html#error
[try]: ref/chap-builtin-cmd.html#try
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

## Related

- [YSH vs. Shell Idioms > Error Handling](idioms.html#error-handling)
- [YSH Fixes Shell's Error Handling (`errexit`)](error-handling.html) - Long
  design doc.


