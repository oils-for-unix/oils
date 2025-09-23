---
default_highlighter: oils-sh
---

Unicode in Oils
===============

Roughly speaking, you can divide programming languages into 3 categories with
respect to Unicode strings:

1. **UTF-8** - Go, Rust, Julia, ..., Oils
1. **UTF-16** - Java, JavaScript, ...
1. **UTF-32** aka Unicode code points - Python 2 and 3, C and C++, ...

So Oils is in the **first** category: it's UTF-8 centric.

Let's see what this means &mdash; in terms your mental model when writing OSH
and YSH, and in terms of the Oils implementation.

<div id="toc">
</div>

## Example: The Length of a String

The Oils runtime has a single `Str` [data type](types.html), which is used by
both OSH and YSH.

A `Str` is an array of bytes, which **may or may not be** UTF-8 encoded.  For
example:

    s=$'\u03bc'      # 1 code point, which is UTF-8 encoded as 2 bytes

    echo ${#s}       # => 1 code point (regardless of locale, right now)

    echo $[len(s)]   # => 2 bytes

That is, the YSH feature `len(mystr)` returns the length in **bytes**.  But the
shell feature `${#s}` *decodes* the string as UTF-8, and returns the length in
**code points**.

Again, this string storage model is like Go and Julia, but different than
JavaScript (UTF-16) and Python (code points).

### Note on bash

`bash` does support multiple lengths, but in a way that depends on global
variables:

    s=$'\u03bc'  # one code point

    echo ${#s}   # => 1, when say LANG=C.UTF-8

    LC_ALL=C     # libc setlocale() called under the hood
    echo ${#s}   # => 2 bytes, now that LC_ALL=C

So bash doesn't seem to fall cleanly in one of the 3 categories above.

It would be interesting to test bash with non-UTF-8 libc locales like Shift JIS
(Japanese), but they are rare.  In practice, the locale almost always C or
UTF-8, so bash and Oils are similar.

But Oils is more strict about UTF-8, and YSH discourages global variables like
`LC_ALL`.

(TODO: For compatibility, OSH should call `setlocale()` when assigning
`LC_ALL=C`.)

<!--
- Python: like bash, strings are logically an array of code points.
- JavaScript: a string is an array of 16-bit code units (UTF-16).

So, unlike those 3 languages, Oils is UTF-8 centric.
-->

## Code Strings and Data Strings

### OSH vs. YSH

For backward compatibility, OSH source files may have **arbitrary bytes**.  For
example, `echo [the literal byte 0xFF]` is a valid source file.

In contrast, YSH source files must be encoded in UTF-8, including its ASCII
subset.  (TODO: Enforce this with `shopt --set utf8_source`)

If you write C-escaped strings, then your source file can be ASCII:

    echo $'\u03bc'   # bash style

    echo u'\u{3bc}'  # YSH style

If you write UTF-8 characters, then your source is UTF-8:

<pre>
echo '&#x03bc;'
</pre>

### Data Encoding

As mentioned, strings in OSH and YSH are arbitrary sequences of **bytes**,
which may or may not be valid UTF-8.

Some operations like length `${#s}` and slicing `${s:1:3}` require the string
to be **valid UTF-8**.  Decoding errors are fatal if `shopt -s
strict_word_eval` is on.

### Passing Data to libc / the Kernel

When passed to external programs, strings are truncated at the first `NUL`
(`'\0'`) byte.  This is a consequence of how Unix and C work.

## Your System Locale Should Be UTF-8

At startup, Oils calls the `libc` function `setlocale()`, which initializes the
global variables from environment variables like `LC_CTYPE` and `LC_COLLATE`.
(For details, see [osh-locale][] and [ysh-locale][].)

[osh-locale]: ref/chap-special-var.html#osh-locale
[ysh-locale]: ref/chap-special-var.html#ysh-locale

These global variables determine how `libc` string operations like `tolower()`
`glob()`, and `regexec()` behave.

For example:

- In `glob()` syntax, does `?` match a byte or a code point?
- In `regcomp()` syntax, does `.` match a byte or a code point?

Oils only supports UTF-8 locales.  If the locale is not UTF-8, Oils prints a
warning to `stderr` at startup.  You can silence it with `OILS_LOCALE_OK=1`.

(Note: GNU readline also calls `setlocale()`, but Oils may or may not link
against GNU readline.)

### Note: Some string operations use libc, and some don't

For example:

- String length like `${#s}` is implemented in Oils code, not `libc`.  It
  currently assumes UTF-8.
  - The YSH `trim()` method is also implemented in Oils, not `libc`.  It
    decodes UTF-8 to detect Unicode spaces.
- On the other hand, `[[ s =~ $pat ]]` is implemented with `libc`, so it's
  affected by the locale settings.
  - This is also true of `(s ~ pat)` in YSH.

## Tips

- The GNU `iconv` program converts text from one encoding to another.

## Summary

Oils is more UTF-8 centric than bash:

- Your system locale should be UTF-8
- Some OSH string operations **assume** UTF-8, because they are implemented
  inside Oils.  They don't use `libc` string functions that potentially support
  multiple locales.

<!--
(TODO: Oils should support `LANG=C LC_ALL=C` in more cases, like for string
length.)
-->

## Appendix: Languages Operations That Involve Unicode

Here are some details.

### OSH / bash

These operations are implemented in Python.

In `osh/string_ops.py`:

- `${#s}` - length in code points
  - OSH gives proper decoding errors; bash returns nonsense
- `${s:1:2}` - index and length are in code points
  - Again, OSH may give decoding errors
- `${x#glob?}` and `${x##glob?}` - see section on glob below

In `builtin/`:

- `printf '%d' \'c` where `c` is an arbitrary character.  This is an obscure
  syntax for `ord()`, i.e. getting an integer from an encoded character.

#### Operations That Use Glob Syntax

The libc functions `glob()` and `fnmatch()` accept a pattern, which may have
the `?` wildcard.  It stands for a single **code point** (in UTF-8 locales),
not a byte.

Word evaluation uses a `glob()` call:

    echo ?.c  # which files match?

These language constructs result in `fnmatch()` calls:

    ${s#?}  # remove one character suffix, quadratic loop for globs

    case $x in ?) echo 'one char' ;; esac

    [[ $x == ? ]]

#### Operations That Involve Regexes (ERE)

Regexes have the wildcard `.`.  Like `?` in globs, it stands for a **code
point**.  They also have `[^a]`, which stands for a code point.

    pat='.'  # single code point
    [[ $x =~ $pat ]]

This construct our **glob to ERE translator** for position info:

    echo ${s/?/x}

#### More Locale-aware operations

- `$IFS` word splitting, which also affects the `shSplit()` builtin
  - Doesn't respect unicode in dash, ash, mksh.  But it does in bash, yash, and
    zsh with `setopt SH_WORD_SPLIT`.  (TODO: Oils could support Unicode in
    `$IFS`.)
- `${foo,}` and `${foo^}` for lowercase / uppercase
  - TODO: For bash compatibility, use `libc` functions?
- `[[ a < b ]]` and `[ a '<' b ]` for sorting
  - TODO: For bash compatibility, use libc `strcoll()`?
- The `$PS1` prompt language has various time `%` codes, which are
  locale-specific.
- In bash, `printf` also has a libc time calls with `%()T`.

Other:

- The prompt width is calculated with `wcswidth()`, which doesn't just count
  code points.  It calculates the **display width** of characters, which is
  different in general.

### YSH

- Eggex matching depends on ERE semantics.
  - `mystr ~ / [ \y01 ] /` 
  - `case (x) { / dot / }`
- [String methods](ref/chap-type-method.html)
  - `Str.{trim,trimStart,trimEnd}` respect unicode space, like JavaScript does
  - TODO: `Str.{upper,lower}` also need unicode case folding
    - are they different than the bash operations?
  - TODO: `s.split()` doesn't have a default "split by space", which should
    probably respect unicode space, like `trim()` does
- [Builtin functions](ref/chap-builtin-func.html)
  - TODO: `for offset, rune in (runes(mystr))` should decode UTF-8, like Go
  - `strcmp()` should do byte-wise and UTF-8 wise comparisons?

### Data Languages

- Decoding JSON/J8 validates UTF-8
- Encoding JSON/J8 decodes and validates UTF-8
  - So we can distinguish valid UTF-8 and invalid bytes like `\yff`

## More Notes

### List of Low-Level UTF-8 Operations

libc:

- `glob()` and `fnmatch()`
- `regexec()`
- `strcoll()` respects `LC_COLLATE`, which bash probably does
- `tolower() toupper()` - will we use these?

In Python:

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

### setlocale() calls made by bash, Python, ...

bash:

    $ ltrace -e setlocale bash -c 'echo'
    bash->setlocale(LC_ALL, "")                    = "en_US.UTF-8"
    ...
    bash->setlocale(LC_CTYPE, "")                  = "en_US.UTF-8"
    bash->setlocale(LC_COLLATE, "")                = "en_US.UTF-8"
    bash->setlocale(LC_MESSAGES, "")               = "en_US.UTF-8"
    bash->setlocale(LC_NUMERIC, "")                = "en_US.UTF-8"
    bash->setlocale(LC_TIME, "")                   = "en_US.UTF-8"
    ...

Notes:

- both bash and GNU readline call `setlocale()`.
- I think `LC_ALL` is sufficient?
- I think `LC_COLLATE` affects `glob()` order, which makes bash scripts
  non-deterministic.
  - We ran into this with `spec/task-runner.sh gen-task-file`, which does a
    glob of `*/*.test.sh`.  James Chen-Smith ran it with the equivalent of
    LANG=C, which scrambled the order.

Python 2 and 3 mostly agree:

    $ ltrace -e setlocale python3 -c 'print()'
    python3->setlocale(LC_CTYPE, nil)              = "C"
    python3->setlocale(LC_CTYPE, "")               = "en_US.UTF-8"

It only calls it for `LC_CTYPE`, not `LC_ALL`.

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
