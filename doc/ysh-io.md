---
default_highlighter: oils-sh
---

YSH Input/Output
================

This doc describes how YSH improves upon I/O in shell.

<!--
TODO:

- bar-g:
  - reading from io.stdin twice in a row produces unexpected results
- Inconsistent naming/usage of read -0 and read --raw-line
- Buffered version of read -0?  Not orthogonal
  -  io.stdin0?  or io.stdinLines vs io.stdin0?

More:

- read --netstr - Length-prefixed reading mode
- Encoding and Decoding
  - JSON lines idiom?  Note that @() is J8 Lines, which is different than JSON
    lines!
-->

<div id="toc">
</div>

## Summary

- The POSIX [read][] builtin is slow because it must read one byte at a time.
  So YSH adds faster ways to read data ([ysh-read][]):
  - Slurping whole files: `read --all`
  - Reading in chunks: `read --num-bytes`
  - Streaming of buffered lines: [io.stdin][]
- YSH adds [J8 Notation][] for encoding and decoding (based on JSON)
  - Writing isn't conflated with encoding (`echo -e`, [printf][])
  - Reading isn't conflated with decoding `\` escapes ([read][])
  - YSH adds `@(command splice)`, which improves on `$(command sub)` and word
    splitting
- YSH supports the NUL-terminated format: `find -print0 | xargs -0`
  - TODO: streaming of buffered chunks?

[printf]: ref/chap-builtin-cmd.html#printf

These YSH constructs make string processing more orthogonal to I/O:

- `${x %.2f}` as a static version of the [printf][] builtin (TODO)
- `${x|html}` and `html"<p>$x</p>"` for safe escaping (TODO)

[io.stdin]: ref/chap-type-method.html#stdin

### Details on Problems with Shell

- `echo $x` is a bug, because `$x` could be `-n`.
  - The YSH [write][] builtin accepts `--`, and [echo][] doesn't accept any
    flags.
- In addition to [read][] being slow, the [mapfile][] builtin is also slow.
- The [read][] builtin is confusing because it respects `\` escapes, unless
  `-r` is passed.
  - These `\` escapes create a mini-language that isn't understood by other
    line-based tools like `grep` and `awk`.  The set of escapes isn't
    consistent between shells.
- There's no way to tell if `$()` strips the trailing newline,.
  - YSH has `read --all`, and `echo hi | read --all` works because `shopt -s
    lastpipe` is the default.

Examples:

    hostname | read --all (&x)
    write -- $x

[json]: ref/chap-builtin-cmd.html#json
[write]: ref/chap-builtin-cmd.html#write
[ysh-read]: ref/chap-builtin-cmd.html#ysh-read

## Tested Invariants

These examples show that YSH I/O is orthogonal and composable.  You can **round
trip** data between YSH data structures and the OS.

### Set Up Test Data

First, let's create files with funny names:

    mkdir -p mydir
    touch   'mydir/file with spaces'
    touch  b'mydir/newline \n file'

And let's list these files in 3 different formats:

    # Line-based: one file spans multiple lines
    find . > lines.txt

    # NUL-terminated
    find . -print0 > 0.bin

    # J8 lines
    redir >j8-lines.txt {
      for path in mydir/* {
        write -- $[toJson(path)]
      }
    }

    head lines.txt j8-lines.txt

Now let's test the invariants.

### File -> String -> File

Start with a file, slurp it into a string, and write it back to an equivalent
file.

    cat lines.txt | read --all

    = _reply  # (Str)

    # suppress trailing newline
    write --end '' -- $_reply > out.txt

    # files are equal
    diff lines.txt out.txt

### File -> Array of Lines -> File (fast)

Start with a file, read it into an array of lines, and write it back to an
equivalent file.

    # newlines removed on reading
    var lines = []
    cat lines.txt | for line in (io.stdin) {
      call lines->append(line)
    }

    = lines  # (List)

    # newlines added
    write -- @lines > out.txt

    # files are equal, even though one path is split across lines
    diff lines.txt out.txt

### File -> Array of Lines -> File (slow)

This idiom can be slow, since `read --raw-line` reads one byte at a time:

    # newlines removed on reading
    var paths = []
    cat lines.txt | while read --raw-line (&path) {
      call paths->append(path)
    }

    = paths   # (List)

    # newlines added
    write -- @paths > out.txt

    # files are equal, even though one path is split across lines
    diff lines.txt out.txt

### NUL File -> Array of Lines -> NUL File (fast)

Start with a file, slurp it into a string, split it into an array, and write it
back to an equivalent file.

    var paths = []
    read --all < 0.bin
    var paths = _reply.split( \y00 )  # split by NUL

    # last \y00 is terminator, not separator
    # TODO: could improve this
    call paths->pop()

    = paths

    # Use NUL separator and terminator
    write --sep b'\y00' --end b'\y00' -- @paths > out0.bin

    diff 0.bin out0.bin

### NUL File -> Array of Lines -> NUL File (slow)

This idiom can be slow, since `read -0` reads one byte at a time:

    var paths = []
    cat 0.bin | while read -0 path {
      call paths->append(path)
    }

    = paths

    # Use NUL separator and terminator
    write --sep b'\y00' --end b'\y00' -- @paths > out0.bin

    diff 0.bin out0.bin

### J8 File -> Array of Lines -> J8 File

Start with a file, slurp it into an array of lines, and write it back to an
equivalent file.

    var paths = @(cat j8-lines.txt)

    = paths

    redir >j8-out.txt {
      for path in (paths) {
        write -- $[toJson8(path)]
      }
    }

    diff j8-lines.txt j8-out.txt

### Array -> File of J8 Lines -> Array

Start with an array, write it to a file, and slurp it back into an array.

    var strs = :| 'with space' b'with \n newline' |
    redir >j8-tmp.txt {
      for s in (strs) {
        write -- $[toJson8(s)]
      }
    }

    cat j8-tmp.txt

    # round-tripped
    assert [strs === @(cat j8-tmp.txt)]

## Reference

### Three Types of I/O

This table characterizes the performance of different ways to read input:

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
  - Buffered, and therefore **fast**
  - <div>

    - [io.stdin][] - loop over lines

    </div>
- tr
  - Unbuffered and **fast** <br/>
    (large chunks)
  - <div>

    - [ysh-read][]: `read --all` and `--num-bytes`
    - Shell `$(command sub)`
    - YSH `@(command splice)`

    </div>
- tr
  - Unbuffered and **slow** <br/>
    (one byte at a time)
  - <div>

    - The POSIX shell [read][] builtin: either without flags, or with short
      flags like `-r -d`
    - The bash [mapfile][] builtin
    - [ysh-read][]:
      - YSH `read --raw-line` (replaces the idiom `IFS= read -r`)
      - YSH `read -0` (replaces the idiom `read -r -d ''`)

    </div>

</table>

[read]: ref/chap-builtin-cmd.html#read

<!--
That is, the POSIX flags to `read` issue many `read(0, 1)` calls.  YSH provides
replacements.
-->

## Related Docs

- [J8 Notation][]
- [JSON](json.html) in Oils
- [Strings](strings.html) &dagger;

[J8 Notation]: j8-notation.html

### Help Topics

- Builtin commands that are encouraged:
  - [write][]
  - [ysh-echo][]
  - [ysh-read][]
  - [json][]
- Builtin commands in shell:
  - [echo][]
  - [printf][]
  - [read][]
  - [mapfile][] - this is also slow in shell
- Types and Methods > [io.stdin][]
- Word Language
  - [command-sub][]
  - [command-splice][] (YSH)

[ysh-echo]: ref/chap-builtin-cmd.html#ysh-echo
[echo]: ref/chap-builtin-cmd.html#echo
[mapfile]: ref/chap-builtin-cmd.html#mapfile

[command-sub]: ref/chap-word-lang.html#command-sub
[command-splice]: ref/chap-word-lang.html#command-splice
