QSN: A Familiar String Interchange Format
=========================================

<style>
.q {
  color: darkred;
}
.comment {
  color: green;
  font-style: italic;
}
.terminal {
  color: darkred;
  font-family: monospace;
}
</style>

QSN ("quoted string notation") is an interchange format for **byte strings**.
Examples:

<pre>
''                           <span class=comment># empty string</span>
'my favorite song.mp3'
'bob<span class=q>\t</span>1.0<span class=q>\n</span>carol<span class=q>\t</span>2.0<span class=q>\n</span>'     <span class=comment># tabs and newlines</span>
'BEL = <span class=q>\x07</span>'                 <span class=comment># byte escape</span>
'mu = <span class=q>\u{03bc}</span>'              <span class=comment># char escapes are encoded in UTF-8</span>
'mu = &#x03bc;'                     <span class=comment># represented literally, not escaped</span>
</pre>

<div id="toc">
</div>

## Why?

QSN has many uses, but one is that [Oil](//www.oilshell.org/) needs a way to
**safely and readably** display filenames in a terminal.

A filename can be any `NUL`-terminated sequence of bytes, including one that
will <span class=terminal>change your terminal color</span>, etc.  Most command
line programs need something like QSN, or they'll have subtle bugs.

For example, as of 2016, [coreutils quotes funny filenames][coreutils] to avoid
the same problem.  However, they didn't specify the format so it can be parsed.

In contrast, QSN can be parsed and printed like JSON.

[in-band]: https://en.wikipedia.org/wiki/In-band_signaling

<!--
The quoting only happens when `isatty()`, so it's not really meant
to be parsed.
-->

[coreutils]: https://www.gnu.org/software/coreutils/quotes.html

## Ways to Remember the Spec

1. Start with [Rust String Literal Syntax](https://doc.rust-lang.org/reference/tokens.html#string-literals)
2. Use **single quotes** instead of double quotes to surround the string (to
   avoid confusion with JSON).

An Analogy:

    Javacript Literals : JSON  ::  Rust String Literals : QSN

## Advantages over JSON Strings

- It can represent any byte string, like `'\x00\xff\x00'`.  JSON can't
  represent **binary data** directly.
- It can represent any code point, like `'\u{01f600}'` for &#x01f600;.  JSON
  needs awkward [surrogate pairs][] to represent this code point.

[surrogate pairs]: https://en.wikipedia.org/wiki/UTF-16#Code_points_from_U+010000_to_U+10FFFF

<!--
## An Analogy

QSN is a little like JSON: it's based on Rust's string literal syntax, just
like JSON is based on JavaScript literal syntax.  Differences:

- It expresses byte strings, which may be UTF-8 encoded text, not character
  strings.  This fits the Unix file system (which has no encoding) and Unix
  kernel APIs like `execve()`, which takes an `argv` array.
- It uses **single quotes** rather than double to avoid confusiong with JSON.



We want a single way to serialize and parse arbitrary byte strings (which may
be encoded in UTF-8 or another encoding.)

- It should be safe to print arbitrary strings to terminals.
- Strings should fit on a line.

TODO: copy content from this page:

<https://github.com/oilshell/oil/wiki/CSTR-Proposal>

-->

## Specification

TODO: The short description above should be sufficient, but we might want to
write it out.

- Special escapes:
  - `\t` `\r` `\n`
  - `\'` `\"`
  - `\\`
  - `\0`
- Byte escapes: `\x7F`
- Character escapes: `\u{03bc}` or `\u{0003bc}`.  These are encoded as UTF-8.

## Implementation Issues

### Three options For Displaying Unicode

QSN denotes byte strings, but byte strings are often encoded with some Unicode
encoding.

A QSN **encoder** has three options for dealing with Unicode.

1. **Decode** UTF-8.  This is useful for showing if the string is valid UTF-8.
   - You can show escaped code points like `'\u03bc'`.  This is ASCII-friendly,
     and can be better for debugging.
   - You can show them literally, like <code>'&#x03bc;'</code>.
2.  Don't decode UTF-8.  Show bytes like `'\xce\xbc'`.

TODO: Show the state machine for detecting and decoding UTF-8.

### Compatibility With Shell Strings

In bash, C-escaped strings are displayed `$'like this\n'`.  A subset of QSN is
compatible with this format.  Example:

```
$'\x01\n'
```

<!--

### Special Chars Emitted

- `\r` `\n` `\t` `\0` (subset of C and shell; Rust has this)
- Everything else is either `\xFF` or `\u03bc`

## Extensions

- QTSV for tables.  This is a priority for Oil.
- JSON-like dicts and lists.  Someone else should run with this!
  - warning: "\\x00\\'" will confuse people.  Programmers don't understand
    backslashes, and language implementers often don't either.
-->


## Notes

- [In-band signaling][in-band]: The fundamental problem with filenames and
  terminals.
- Comparison with Python's `repr()`:
  - A single quote in Python is `"'"`, whereas it's `'\''` in QSN
  - Python has both `\uxxxx` and `\Uxxxxxxxx`, whereas QSN has the more natural
    `\u{xxxxxx}`.

## Use Case: `set -x` format (`xtrace`)

When arguments don't have any spaces, there's no ambiguity:

```
$ set -x
$ echo two args
+ echo two args
```

Here we need quotes to show that the `argv` array has 3 elements:

```
$ set -x
$ x='a b'
$ echo "$x" c
+ echo 'a b' c
```

And we want the trace to fit on a single line, so we print a QSN string with
`\n`:

```
$ set -x
$ x=$'a\nb'
$ echo "$x" c
+ echo $'a\nb' c
```

Here's an example with unprintable characters:

```
$ set -x
$ x=$'\e\001'
$ echo "$x"
+ echo $'\x1b\x01'
```
