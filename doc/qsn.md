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
.an {
  color: darkgreen;
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

It's meant to be emitted and parsed by programs written in different languages,
as UTF-8 or JSON are.  It's both human- and machine-readable.

[Oil](/) understands QSN, and other Unix shells should too.

<div id="toc">
</div>

## Why?

QSN has many uses, but one is that [Oil](//www.oilshell.org/) needs a way to
safely and readably **display filenames** in a terminal.

Filenames may contain arbitrary bytes, including ones that will <span
class=terminal>change your terminal color</span>, and more.  Most command line
programs need something like QSN, or they'll have subtle bugs.

For example, as of 2016, [coreutils quotes funny filenames][coreutils] to avoid
the same problem.  However, they didn't specify the format so it can be parsed.
In contrast, QSN can be parsed and printed like JSON.

[in-band]: https://en.wikipedia.org/wiki/In-band_signaling

<!--
The quoting only happens when `isatty()`, so it's not really meant
to be parsed.
-->

### More Use Cases

- For `set -x` in shell.  Like filenames, Unix `argv` arrays may contain
  arbitrary bytes.  See the example below.
- To pack arbitrary bytes on a **single line**, e.g. for line-based tools like
  [grep]($xref), [awk]($xref), and [xargs]($xref).  QSN strings never contain
  literal newlines.
- As a building block for larger specifications, like [QTSV](qtsv.html).
- To transmit arbitrary bytes over channels that can only represent ASCII or
  UTF-8 (e.g. e-mail, Twitter).

[surrogate pairs]: https://en.wikipedia.org/wiki/UTF-16#Code_points_from_U+010000_to_U+10FFFF



[coreutils]: https://www.gnu.org/software/coreutils/quotes.html

## Specification

### A Short Description

1. Start with [Rust String Literal Syntax](https://doc.rust-lang.org/reference/tokens.html#string-literals)
2. Use **single quotes** instead of double quotes to surround the string.  This
   is mainly to to avoid confusion with JSON.

### An Analogy

<pre>

     <span class=an>JavaScript Object Literals</span>   are to    <span class=an>JSON</span>
as   <span class=an>Rust String Literals</span>         are to    <span class=an>QSN</span>

</pre>

But QSN is **not** tied to either Rust or shell, just like JSON isn't tied to
JavaScript.

It's a **language-independent format** like UTF-8 or HTML.  We're only
borrowing a design, so that it's well-specified and familiar.

### Full Spec

TODO: The short description above should be sufficient, but we might want to
write it out.

- Special escapes:
  - `\t` `\r` `\n`
  - `\'` `\"`
  - `\\`
  - `\0`
- Byte escapes: `\x7F`
- Character escapes: `\u{03bc}` or `\u{0003bc}`.  These are encoded as UTF-8.

## Advantages over JSON Strings

- QSN can represent any byte string, like `'\x00\xff\x00'`.  JSON can't
  represent **binary data** directly.
- QSN can represent any code point, like `'\u{01f600}'` for &#x01f600;.  JSON
  needs awkward [surrogate pairs][] to represent this code point.

## Implementation Issues

### Compatibility With Shell Strings

In bash, C-escaped strings are displayed `$'like this\n'`.  A **subset** of QSN is
compatible with this syntax.  Examples:

```
$'\x01\n'  # removing $ makes it valid QSN

$'\0065'   # octal escape is invalid in QSN
```

### Three Options For Displaying Unicode

QSN denotes byte strings, but byte strings are often interpreted with a Unicode
encoding.  A QSN **encoder** has three options for dealing with Unicode:

1. **Don't decode** anything.  Show bytes like `'\xce\xbc'`.
1. Speculatively **decode UTF-8**.  QSN encoding should never fail; it should
   only fall back to byte escapes like `\xff`.  This is useful for showing if
   the string is valid UTF-8.  After decoding a valid UTF-8 sequence, there are
   two options:
   - You can **show escaped code points** like `'\u03bc'`.  This is ASCII-friendly,
     and can be better for debugging.
   - You can **show them literally**, like <code>'&#x03bc;'</code>.

TODO: Show the state machine for detecting and decoding UTF-8.


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


## Design Notes

The general idea: Rust string literals are like C and JavaScript string
literals, without cruft like octal (`\755` or `\0755` &mdash; which is it?) and
vertical tabs (`\v`).

Comparison with shell strings:

- `'Single quoted strings'` in shell can't represent arbitrary byte strings.
- `$'C-style shell strings\n'` strings are similar to QSN, but have cruft like
  octal and `\v`.
- `"Double quoted strings"` have unneeded features like `$var` and `$(command
  sub)`.

Comparison with Python's `repr()`:

- A single quote in Python is `"'"`, whereas it's `'\''` in QSN
- Python has both `\uxxxx` and `\Uxxxxxxxx`, whereas QSN has the more natural
  `\u{xxxxxx}`.

[In-band signaling][in-band] is the fundamental problem with filenames and
terminals.
  
## Example: `set -x` format (`xtrace`)

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
