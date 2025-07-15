---
in_progress: true
default_highlighter: oils-sh
---

YSH I/O Builtins
================

This doc describes how YSH I/O improves upon shell I/O:

- The POSIX [read][] builtin is slow, so YSH adds faster options.
- Reading isn't conflated with `\` decoding
- Writing isn't conflated with encoding (`printf`)
- YSH adds `@(split command sub)`, rather than relying on `$()` and word
  splitting

<!--
TODO:

- bar-g:
  - reading from io.stdin twice in a row produces unexpected results
- buffered version of read -0: io.stdin0?  or io.stdinLines vs io.stdin0?
- read --netstr
- Encoding and Decoding
  - Note that @() is J8 Lines, which is different than JSON lines!
  - JSON lines idiom?

- should run all this code, like ysh-tour.md
-->

<div id="toc">
</div>

## Intro

POSIX shell has overlapping and quirky constructs for doing I/O:

- write with the `echo` and `printf` builtins
- read with `read` (which is slow)
- the `$(command sub)` construct
- Bash has `mapfile` and `readarray` (also slow)

YSH rationalizes I/O with:

- A new `write` builtin
- Long flags to `read`, like `--all`
- The distinction between `$(command sub)` and `@(split command sub)`
- [io.stdin][] for buffered I/O

YSH also has orthogonal mechanisms for string processing:

- A set of data languages called [J8 Notation](j8-notation.html).
- `${x %.2f}` as a static version of the `printf` builtin (TODO)
- `${x|html}` and `html"<p>$x</p>"` for safe escaping (TODO)

These are discussed in more detail the [strings](strings.html) doc.

[io.stdin]: ref/chap-type-method.html#stdin

## Problems With Shell

- `echo` is flaky because `echo $x` is a bug.  `$x` could be `-n`.
  - YSH `write` accepts `--`.
- The `read` builtin
  - is slow because it always reads one byte at a time.
  - is confusing because it respects `\` escapes, unless `-r` is passed.
    These `\` escapes create a mini-language that isn't understood by other
    line-based tools like `grep` and `awk`.  The set of escapes isn't
    consistent between shells.
- There's no way to tell if `$()` strips the trailing newline,.
  - YSH has `read --all`, and allows `echo hi | read --all`, because `shopt -s
    lastpipe` is the default.

Examples:

    hostname | read --all (&x)
    write -- $x

## Summary of YSH features

### write

- `--sep`: Characters to separate each argument.  (Default: space)
- `--end`: Characters to terminate the whole invocation.  (Default: newline)
- `-n`: A synonym for `-end ''`.

### reading

- The `read` builtin, documented under [ysh-read][]
  - unbuffered and fast: `--all --num-bytes`
  - unbuffered and slow: --raw-line -0`
- [io.stdin][] - buffered line reading
- `$(command sub)` removes the trailing newline, if any
- `@(split command sub)` uses J8 Lines

[ysh-read]: ref/chap-builtin-cmd.html#ysh-read

## Invariants

These examples show that YSH I/O is orthogoanl and composable.  There are ways
to "round trip" data between the OS and YSH data structures.

### File -> String -> File

    cat input.txt | read --all

    # suppress the newline
    write --end '' -- $_reply > output.txt

    diff input.txt output.txt  # files are equal

### File -> Array of Lines -> File

    # newlines stripped
    var lines = []
    cat input.txt | for line in (io.stdin) {
      call lines->append(line)
    }

    # newlines added
    write -- @lines > output.txt

    diff input.txt output.txt  # files are equal

### NUL File -> Array of Lines -> NUL File

TODO: `read -0`

### Array -> File of J8 Lines -> Array

    var strs = [b'one\ntwo', 'three four']
    fopen >tmp.txt {
      for s in (strs) {
        write -- $[toJson8(s)]
      }
    }

    cat tmp.txt

    var decoded = @(cat tmp.txt)  # round-tripped
    assert [strs === decoded]

## Three Types of I/O

This table summarizes the performance characteristics of different ways to read
input:

<style>
table {
  margin-left: 2em;
  background-color: #eee;
}
table code {
  color: green;
}
thead {
  background-color: white;
}
td {
  vertical-align: top;
}
</style>

<table cellpadding="10" cellspacing="5">

- thead
  - Performance
  - Shell Constructs
- tr
  - Unbuffered and **slow** <br/>
    (one byte at a time)
  - The POSIX shell [read][] builtin: with no flags, or short flags like `-r
    -d`<br/>
    YSH `read --raw-line` (replaces the idiom `IFS= read -r`) <br/>
    YSH `read -0` (replaces the idiom `read -r -d ''`) <br/>
    See [ysh-read][] <br/>
- tr
  - Unbuffered and **fast** <br/>
    (large chunks)
  - `read --all` and `--num-bytes` (see [ysh-read][]) <br/>
     Shell `$(command sub)` <br/>
     YSH `@(split command sub)` <br/>
- tr
  - Buffered, and therefore **fast**
  - [io.stdin][] - loop over lines

</table>

[read]: ref/chap-builtin-cmd.html#read

<!--
That is, the POSIX flags to `read` issue many `read(0, 1)` calls.  YSH provides
replacements.
-->

## Related

- [JSON](json.html) in Oils
