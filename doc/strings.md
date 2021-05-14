---
default_highlighter: oil-sh
in_progress: true
---

Strings: Quoting and Interpolation
==================================

- Usage tips
- Reference

In fact, it literally started with Python's `Grammar/Grammar` file.

<div id="toc">
</div>

## Quick Reference

    echo unquoted          # bare words are allowed in command mode

    echo 'with spaces'     # single quoted string
    var s = 'with spaces'

    # Raw single quoted string, to emphasize literal backslashes
    var s = r'C:\Program Files\'

    # C-escaped single quoted string
    var line = $'foo\n'

    # double quoted with safe interpolation (TODO)
    echo "<p>hello $[name]</p>"       # default_escaper must be set
    echo "<p>hello ${name|html}</p>"  # explicit escaper

    # double quoted with unsafe interpolation
    echo "hello $name"
    echo "hello ${name}_suffix"       # braces delimit variable name

    echo $(date +%x)                  # command sub

Still TODO:

    cat <<< '''
       one
       two
       '''

    cat <<< $'''
       mu = \u{3bc}
       nul = \x00
       '''

    var s = """
       multiline with ${vars}
       $(date +%x)
       ${.myproc}
       """

## Summary

This section summarizes the advice below.

Preference order:

- unquoted strings (command mode only)
- single quoted strings
  - when you need to express special characters
  - QSN
- double quoted strings
  - with `$[]` interpolation
  - with `${}` interpolation

## Use Unquoted Strings in Command Mode

Shell is unique!  You don't have to quote strings.

- link: command vs. expression mode

and quoted strings in expression mode

## Two Kinds of Single-Quoted Strings

### Raw with `r'C:\Program Files\'`

- TODO: `parse_raw_strings`

### C-Escaped With `$'foo\n'` 

- Use the [QSN]($xref) subset

## Use Double-Quoted Strings For Interpolation

### Implicit Safe Interpolation with `$[x]` (TODO)

- Use `$[x]` for safe interpolation
  - Respects `shopt --set default_escaper`

### Explicit Safe Interpolation With `${x|html}` (TODO)

- Use `${x|html}` for safe interpolation

Note you can have bugs if you use the wrong escaper!

### Raw Interpolation with `$x` (may be unsafe)

- Use `$x` or `${x}`
  - These are identical except for syntax
- Useful for log messages, which aren't security sensitive

### Command Sub `$(echo hi)` 

### Fast Command Sub `${.myproc}` (stdout capture)

Note that only words are allowed here; not full commands.  Wrap other commands
in a proc.

- Using `write_to_buffer`

TODO:

   echo ${.myproc foo|html}  # I think this should be supported

## Codecs and Escapers

For `${x|html}` and `${.myproc|html}`

TODO

- how to register them
- wasm plugins?

## Use Triple Quoted Strings Instead of Here Docs (TODO)

TODO

## Concatenate With `"$str1$str2"`

Or `"${str1}${str2}"`

- is `s ++ t` valid?. It isn't necessary for strings and lists
  - `%(@a @b)` is the same for lists
  - does this Python syntax also work?  `[*a, *b]`
  - Dicts: `{d, **e}` might be better

### Avoid Concatenation in a Loop

    setvar s = "${s}${suffix}"

## Append with Two Styles

Since there is no `++` operator, there is no `++=` operator.

### `echo`, `printf`, `write`, and `${.myproc}` (`write_to_buffer`)

echo, printf, and write have their output captured.

    proc p(arg) {
      ### A proc that has its output captured quickly.

      echo $arg
      write two

      const x = 'three'
      printf '%s\n' $x

      # newline for interactive testing, but not when captured
      if ! shopt -q write_to_buffer {
        echo  
      }
    }

    echo ${.p one}  # $'one\ntwo\nthree\n'

### `push` and `join`

    var buf = %()
    push :buf 'one '
    push :buf $'two\n'
    echo $join(buf)

## Appendix A: Deprecated Shell Constructs

- here docs!
  - Use tripled quoted strings.
- Backticks for command sub
  - Use `$(echo hi)`
- Arithmetic substitution like `$((1 + 2))`
  - Use Oil expressions: `$[1 + 2]`
- `${x%%prefix}` and so forth
  - Use builtin Oil functions (TODO)
- Unused: bash `$""` for localization?

## Appendix B: Related Documents

- Expression Language
- [QSN](qsn.html)

