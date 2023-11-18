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

That is, its Unicode support is like Go, Rust, Julia, and Swift, as opposed to
JavaScript, and Python (despite its Python heritage).  The former languages use
UTF-8, and the latter have the notion of "multibyte characters".

## A Mental Model

### Program Encoding

Shell **programs** should be encoded in UTF-8 (or its ASCII subset).  Unicode
characters can be encoded directly in the source:

<pre>
echo '&#x03bc;'
</pre>

or denoted in ASCII with C-escaped strings:

    echo $'[\u03bc]'

(Such strings are preferred over `echo -e` because they're statically parsed.)

### Data Encoding

Strings in OSH are arbitrary sequences of **bytes**, which may be valid UTF-8.
Details:

- When passed to external programs, strings are truncated at the first `NUL`
  (`'\0'`) byte.  This is a consequence of how Unix and C work.
- Some operations like length `${#s}` and slicing `${s:1:3}` require the string
  to be **valid UTF-8**.  Decoding errors are fatal if `shopt -s
  strict_word_eval` is on.

## List of Unicode-Aware Operations in OSH / bash

### Length / Slicing

- `${#s}` -- length in code points (buggy in bash)
  - Note: `len(s)` counts bytes.
- `${s:1:2}` -- offsets in code points

### Globs

Globs have character classes `[^a]` and `?`.

This is a `glob()` call:

    echo my?glob

These glob patterns are `fnmatch()` calls:

    case $x in ?) echo 'one char' ;; esac
    [[ $x == ? ]]
    ${s#?}  # remove one character suffix, quadratic loop for globs

This uses our glob to ERE translator for *position* info:

    echo ${s/?/x}

### Regexes (ERE)

Regexes have character classes `[^a]` and `.`.

- `[[ $x =~ $pat ]]` where `pat='.'`

### More bash operations

- [[ a < b ]] and [ a '<' b ] for sorting
- ${foo,} and ${foo^} for lowercase / uppercase
- `printf '%d' \'c` where `c` is an arbitrary character.  This is an obscure
  syntax for `ord()`, i.e. getting an integer from an encoded character.

Local-aware operations:

- Prompt string has time, which is locale-specific.
- In bash, `printf` also has time.

Other:

- The prompt width is calculated with `wcswidth()`, which doesn't just count
  code points.  It calculates the **display width** of characters, which is
  different in general.

## YSH-Specific

- Eggex matching depends on ERE semantics.
  - `mystr ~ / [ \xff ] /` 
  - `case (x) { / dot / }`
- `for offset, rune in (mystr)` decodes UTF-8, like Go
- `Str.{trim,trimLeft,trimRight}` respect unicode space, like JavaScript does
- `Str.{upper,lower}` also need unicode case folding
- `split()` respects unicode space?

## Data Languages

- Decoding JSON/J8 needs to validate UTF-8
- Encoding JSON/J8 needs to decode/validate UTF-8
  - Decoding to print `\u{123456}` in `j""` strings

## Tips

- The GNU `iconv` program converts text from one encoding to another.

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
