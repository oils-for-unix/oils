---
default_highlighter: oil-sh
in_progress: yes
---

Notes on Unicode in Shell
=========================

<div id="toc">
</div>

## Philosophy

Oil's is UTF-8 centric, unlike `bash` and other shells.

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

## List of Unicode-Aware Operations in Shell

- `${#s}` -- length in code points
  - Note: `len(s)` counts bytes.
- `${s:1:2}` -- offsets in code points
- `${x#?}` -- a glob for a single character

Where bash respects it:

- [[ a < b ]] and [ a '<' b ] for sorting
- ${foo,} and ${foo^} for lowercase / uppercase
- Any operation that uses glob, because it has `?` for a single character,
  character classes like `[[:alpha:]]`, etc.
  - `case $x in ?) echo 'one char' ;; esac`
  - `[[ $x == ? ]]`
  - `${s#?}` (remove one character)
  - `${s/?/x}` (note: this uses our glob to ERE translator for position)
- `printf '%d' \'c` where `c` is an arbitrary character.  This is an obscure
  syntax for `ord()`, i.e. getting an integer from an encoded character.

Local-aware operations:

- Prompt string has time, which is locale-specific.
- In bash, `printf` also has time.

Other:

- The prompt width is calculated with `wcswidth()`, which doesn't just count
  code points.  It calculates the **display width** of characters, which is
  different in general.

## Tips

- The GNU `iconv` program converts text from one encoding to another.

## Implementation Notes

Unlike bash and CPython, Oil doesn't call `setlocale()`.  (Although GNU
readline may call it.)

It's expected that your locale will respect UTF-8.  This is true on most
distros.  If not, then some string operations will support UTF-8 and some
won't.

For example:

- String length like `${#s}` is implemented in Oil code, not libc, so it will
  always respect UTF-8.
- `[[ s =~ $pat ]]` is implemented with libc, so it is affected by the locale
  settings.  Same with Oil's `(x ~ pat)`.

TODO: Oil should support `LANG=C` for some operations, but not `LANG=X` for
other `X`.

