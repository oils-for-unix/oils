---
in_progress: true
---

I/O Builtins in Oil
===================

In POSIX shell, the `echo`, `printf`, `read` builtins, and the `$(command sub)`
construct, are overlapping and quirky.

Oil fixes this with `write`, long flags to `read`, `$(string sub)`, `@(array
sub)`, and [QSN](qsn.html).

TODO: Also see [JSON](json.html).


<!-- cmark.py expands this -->
<div id="toc">
</div>

## Summary of Constructs

- `write`: `--sep` and `--end`
- `read`: `--line`, `--lines`, and `--all` (or `--all-lines`?)
- `$(string sub)` removes the trailing newline, if any
- `@(array sub)` splits by `IFS=$'\n'`

## Buffered vs. Unbuffered

- The POSIX flags to `read` issue many `read(0, 1)` calls.  They do it
  byte-by-byte.
- The `--long` flags to `read` use buffered I/O.

## Invariants

    # This will get messed up with newlines, and empty strings.
    IFS='\n'
    @(write -- @myarray)
  
    # This will give you back an array
    @(write -q -- @myarray)
  
  
### Array -> QSN Lines -> Array

This is one way to make a copy of an array

    write -q -- @myarray | read --lines -q :otherarray
  
In contrast, this doesn't work when the elements have newlines:

    var myarray = %( 'bad\n' )
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

## read doesn't lose information, while $() and @() do

Compare:

    var s = $(hostname)       # strips trailing newline
    hostname | read --all :s  # preserves it

And:

    var lines = @(cat file.txt)
    cat file.txt | read --lines :lines
