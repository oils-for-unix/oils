---
in_progress: true
default_highlighter: oil-sh
---

YSH I/O Builtins
================

POSIX shell has overlapping and quirky constructs for doing I/O:

- the builtins `echo`, `printf`, and `read`
- the `$(command sub)` construct
- Bash has `mapfile` and `readarray`

YSH rationalizes I/O with:

- A new `write` builtin
- Long flags to `read`, like `--line` and `--all`
- The distinction between `$(string sub)` and `@(array sub)`
- The [QSN](qsn.html) serialization format.

YSH also has orthogonal mechanisms for string processing:

- `${.myproc arg}` and `@{.myproc arg}` are an optimization (TODO)
- `${x %.2f}` as a static version of the `printf` builtin (TODO)
- `${x|html}` for safe escaping (TODO)

These are discussed in more detail the [strings](strings.html) doc.

<!-- TODO: should run all this code as in tour.md -->

<div id="toc">
</div>

## Problems With Shell

- `echo` is flaky because `echo $x` is a bug.  `$x` could be `-n`.
  - YSH `write` accepts `--`.
- `read` is flaky good because the `-r` flag to ignore `\` line continuations
  isn't the default.  The `\` creates a mini-language that isn't understood by
  other line-based tools like `grep` and `awk`.
  - YSH has `read --line`.
- There's no way to tell if `$()` strips the trailing newline,.
  - YSH has `read --all`, as well as lastpipe being on.

Example:

    hostname | read --all :x
    write -- $x

## Summary of YSH features

- `write`: `--qsn`, `--sep`, `--end`
- `read`: `--qsn`, `--line`, `--lines`, and `--all` (or `--all-lines`?)
- `$(string sub)` removes the trailing newline, if any
- `@(array sub)` splits by IFS
  - TODO: should it split by `IFS=$'\n'`?

### write

- `-sep`: Characters to separate each argument.  (Default: newline)
- `-end`: Characters to terminate the whole invocation.  (Default: newline)
- `-n`: A synonym for `-end ''`.

## Buffered vs. Unbuffered

- The POSIX flags to `read` issue many `read(0, 1)` calls.  They do it
  byte-by-byte.
- The `--long` flags to `read` use buffered I/O.

## Invariants

Here are some design notes on making the I/O builtins orthogonal and
composable.  There should be clean ways to "round trip" data between the OS and
YSH data structures.

### Problem

    # This will get messed up with newlines, and empty strings.
    IFS=$'\n'
    var lines1 = @(write -- @myarray)
  
    # This will give you back an array
    var lines2 = @(write --qsn -- @myarray)
  
### Array -> QSN Lines -> Array

This is one way to make a copy of an array

    write --qsn -- @myarray | read --lines --qsn :otherarray
  
In contrast, this doesn't work when the elements have newlines:

    var myarray = :| 'bad\n' |
    write -- @myarray | read --lines :otherarray

### File -> Array -> File

    cat input.txt | read --all-lines :myarray

    # suppress the newline
    write --sep '' --end '' -- @myarray > output.txt

    diff input.txt output.txt  # should be equal

### File -> String -> File

    cat input.txt | read --all :x

    # suppress the newline
    write --end '' $x > output.txt

    diff input.txt output.txt  # should be equal

## Related

- [JSON](json.html) support.
