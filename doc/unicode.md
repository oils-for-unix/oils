---
default_highlighter: oils-sh
in_progress: yes
---

Notes on Unicode in Shell
=========================

<div id="toc">
</div>

## Philosophy

Oils is UTF-8 centric, unlike `bash` and other shells.

That is, its Unicode support is like Go, Rust, Julia, and Swift, and not like
Python or JavaScript.  The former languages internally represent strings as
UTF-8, while the latter use arrays of code points or UTF-16 code units.

## A Mental Model

### Program Encoding - OSH vs. YSH

- The source files of OSH programs may have arbitrary bytes, for backward
  compatibility.
- The source files of YSH programs should be should be encoded in UTF-8 (or its
  ASCII subset).  TODO: Enforce this with `shopt --set utf8_source`

Unicode characters can be encoded directly in the source:

<pre>
echo '&#x03bc;'
</pre>

or denoted in ASCII with C-escaped strings:

    echo $'\u03bc'   # bash style

    echo u'\u{3bc}'  # YSH style

(Such strings are preferred over `echo -e` because they're statically parsed.)

### Data Encoding

Strings in OSH are arbitrary sequences of **bytes**, which may or may not be
valid UTF-8.  Details:

- When passed to external programs, strings are truncated at the first `NUL`
  (`'\0'`) byte.  This is a consequence of how Unix and C work.
- Some operations like length `${#s}` and slicing `${s:1:3}` require the string
  to be **valid UTF-8**.  Decoding errors are fatal if `shopt -s
  strict_word_eval` is on.

## List of Features That Respect Unicode

### OSH / bash

These operations are implemented in Python.

In `osh/string_ops.py`:

- `${#s}` -- length in code points (buggy in bash)
  - Note: YSH `len(s)` returns a number of bytes, not code points.
- `${s:1:2}` -- index and length are a number of code points
- `${x#glob?}` and `${x##glob?}` (see below)

In `builtin/`:

- `printf '%d' \'c` where `c` is an arbitrary character.  This is an obscure
  syntax for `ord()`, i.e. getting an integer from an encoded character.

More:

- `$IFS` word splitting.  Affects `shSplit()` builtin
  - Doesn't respect unicode in dash, ash, mksh.  But it does in bash, yash, and
    zsh with `setopt SH_WORD_SPLIT`.
  - TODO: Oils should probably respect it
- `${foo,}` and `${foo^}` for lowercase / uppercase
  - TODO: doesn't respect unicode
- `[[ a < b ]]` and `[ a '<' b ]` for sorting
  - these can use libc `strcoll()`?

#### Globs

Globs have character classes `[^a]` and `?`.

This pattern results in a `glob()` call:

    echo my?glob

These patterns result in `fnmatch()` calls:

    case $x in ?) echo 'one char' ;; esac

    [[ $x == ? ]]

    ${s#?}  # remove one character suffix, quadratic loop for globs

This uses our glob to ERE translator for *position* info:

    echo ${s/?/x}

#### Regexes (ERE)

Regexes have character classes `[^a]` and `.`:

    pat='.'  # single "character"
    [[ $x =~ $pat ]]

#### Locale-aware operations

- Prompt string has time, which is locale-specific.
- In bash, `printf` also has time.

Other:

- The prompt width is calculated with `wcswidth()`, which doesn't just count
  code points.  It calculates the **display width** of characters, which is
  different in general.

### YSH

- Eggex matching depends on ERE semantics.
  - `mystr ~ / [ \xff ] /` 
  - `case (x) { / dot / }`
- `Str.{trim,trimLeft,trimRight}` respect unicode space, like JavaScript does
- TODO: `Str.{upper,lower}` also need unicode case folding
- TODO: `s.split()` doesn't have a default "split by space", which should
  probably respect unicode space, like `trim()` does
- TODO: `for offset, rune in (runes(mystr))` decodes UTF-8, like Go

Not unicode aware:

- `strcmp()` does byte-wise and UTF-8 wise comparisons?

### Data Languages

- Decoding JSON/J8 validates UTF-8
- Encoding JSON/J8 decodes and validates UTF-8
  - So we can distinguish valid UTF-8 and invalid bytes like `\yff`

## Implementation Notes

Unlike bash and CPython, Oils doesn't call `setlocale()`.  (Although GNU
readline may call it.)

It's expected that your locale will respect UTF-8.  This is true on most
distros.  If not, then some string operations will support UTF-8 and some
won't.

For example:

- String length like `${#s}` is implemented in Oils code, not libc, so it will
  always respect UTF-8.
- `[[ s =~ $pat ]]` is implemented with libc, so it is affected by the locale
  settings.  Same with Oils `(x ~ pat)`.

TODO: Oils should support `LANG=C` for some operations, but not `LANG=X` for
other `X`.

### List of Low-Level UTF-8 Operations

libc:

- `glob()` and `fnmatch()`
- `regexec()`
- `strcoll()` respects `LC_COLLATE`, which bash probably does

Our own:

- Decode next rune from a position, or previous rune
  - `trimLeft()` and `${s#prefix}` need this
- Decode UTF-8
  - J8 encoding and decoding need this
  - `for r in (runes(x))` needs this
  - respecting surrogate half
    - JSON needs this
- Encode integer rune to UTF-8 sequence
  - J8 needs this, for `\u{3bc}` (currently in `data_lang/j8.py Utf8Encode()`)

Not sure:

- Case folding
  - both OSH and YSH have uppercase and lowercase

## Tips

- The GNU `iconv` program converts text from one encoding to another.

<!--
## Spec Tests

June 2024 notes:

- `spec/var-op-patsub` has failing cases, e.g. `LC_ALL=C`
  - ${s//?/a}
- glob() and fnmatch() seem to be OK?   As long as locale is UTF-8.

-->

<!--

What libraries are we using?

TODO: Make sure these are UTF-8 mode, regardless of LANG global variables?

Or maybe we punt on that, and say Oils is only valid in UTF-8 mode?  Need to
investigate the API more.

- fnmatch()
- glob()
- regcomp/regexec()

- Are we using any re2c unicode?  For JSON?
- upper() and lower()?  isupper() is lower()
  - Need to sort these out

-->
