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

.attention {
  font-size: x-large;
  background-color: #DEE;
  margin-left: 1em;
  margin-right: 1em;
  padding-left: 1em;
  padding-right: 1em;
}
</style>

&nbsp;

&nbsp;

<div class=attention>

&nbsp;

As of January 2024, QSN has been replaced by [J8 Notation](j8-notation.html).
They're very similar, but J8 Notation is more "harmonized" with JSON.

&nbsp;

</div>

&nbsp;

&nbsp;

&nbsp;

&nbsp;

&nbsp;

QSN ("quoted string notation") is a data format for **byte strings**.
Examples:

<pre>
''                           <span class=comment># empty string</span>
'my favorite song.mp3'
'bob<span class=q>\t</span>1.0<span class=q>\n</span>carol<span class=q>\t</span>2.0<span class=q>\n</span>'     <span class=comment># tabs and newlines</span>
'BEL = <span class=q>\x07</span>'                 <span class=comment># byte escape</span>
'mu = <span class=q>\u{03bc}</span>'              <span class=comment># Unicode char escape</span>
'mu = &#x03bc;'                     <span class=comment># represented literally, not escaped</span>
</pre>

It's an adaptation of Rust's string literal syntax with a few use cases:

- To print filenames to a terminal.  Printing arbitrary bytes to a
  terminal is bad, so programs like [coreutils]($xref) already have [informal
  QSN-like formats][coreutils-quotes].
- To exchange data between different programs, like [JSON][] or UTF-8.  Note
  that JSON can't express arbitrary byte strings.
- To solve the "[framing problem](framing.html)" over pipes.  QSN represents
  newlines like `\n`, so literal newlines can be used to delimit records.
  
Oil uses QSN because it's well-defined and parsable.  It's both human- and
machine-readable.

Any programming language or tool that understands JSON should also understand
QSN.

[JSON]: https://json.org

<div id="toc">
</div>

<!--
### The Terminal Use Case

Filenames may contain arbitrary bytes, including ones that will <span
class=terminal>change your terminal color</span>, and more.  Most command line
programs need something like QSN, or they'll have subtle bugs.

For example, as of 2016, [coreutils quotes funny filenames][coreutils] to avoid
the same problem.  However, they didn't specify the format so it can be parsed.
In contrast, QSN can be parsed and printed like JSON.

-->

<!--
The quoting only happens when `isatty()`, so it's not really meant
to be parsed.
-->

## Important Properties

- QSN can represent **any byte sequence**.
- Given a QSN-encoded string, any 2 decoders must produce the same byte string.
  (On the other hand, encoders have flexibility with regard to escaping.)
- An encoded string always fits on a **single line**.  Newlines must be encoded as
  `\n`, not literal.
- A encoded string always fits in a **TSV cell**.  Tabs must be encoded as `\t`,
  not literal.
- An encoded string can itself be **valid UTF-8**.
  - Example: `'μ \xff'` is valid UTF-8, even though the decoded string is not.
- An encoded string can itself be **valid ASCII**.
  - Example: `'\xce\xbc'` is valid ASCII, even though the decoded string is
    not.

## More QSN Use Cases

- To pack arbitrary bytes on a **single line**, e.g. for line-based tools like
  [grep]($xref), [awk]($xref), and [xargs]($xref).  QSN strings never contain
  literal newlines or tabs.
- For `set -x` in shell.  Like filenames, Unix `argv` arrays may contain
  arbitrary bytes.  There's an example in the appendix.
  - `ps` has to display untrusted `argv` arrays.
  - `ls` has to display untrusted filenames.
  - `env` has to display untrusted byte strings.  (Most versions of `env` don't
    handle newlines well.)
- As a building block for larger specifications, like [QTT][].
- To transmit arbitrary bytes over channels that can only represent ASCII or
  UTF-8 (e.g. e-mail, Twitter).

[QTT]: qtt.html
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

## Advantages Over JSON Strings

- QSN can represent any byte string, like `'\x00\xff\x00'`.  JSON can't
  represent **binary data** directly.
- QSN can represent any code point, like `'\u{01f600}'` for &#x01f600;.  JSON
  needs awkward [surrogate pairs][] to represent this code point.

## Implementation Issues

### How Does a QSN Encoder Deal with Unicode?

The input to a QSN encoder is a raw **byte string**.  However, the string may
have additional structure, like being UTF-8 encoded.

The encoder has three options to deal with this structure:

1. **Don't decode** UTF-8.  Walk through bytes one-by-one, showing unprintable
   ones with escapes like `\xce\xbc`.  Never emit escapes like `\u{3bc}` or
   literals like <code>&#x03bc;</code>.  This option is OK for machines, but
   isn't friendly to humans who can read Unicode characters.

Or **speculatively decode** UTF-8.  After decoding a valid UTF-8 sequence,
there are two options:

2. Show **escaped code points**, like `\u{3bc}`.  The encoded string is limited
   to the ASCII subset, which is useful in some contexts.

3. Show them **literally**, like <code>&#x03bc;</code>.

QSN encoding should never fail; it should only fall back to byte escapes like
`\xff`.  TODO: Show the state machine for detecting and decoding UTF-8.

Note: Strategies 2 and 3 indicate whether the string is valid UTF-8.

### Which Bytes Should Be Hex-Escaped?

The reference implementation has two functions:

- `IsUnprintableLow`: any byte below an ASCII space `' '` is escaped
- `IsUnprintableHigh`: the byte `\x7f` and all bytes above are escaped, unless
  they're part of a valid UTF-8 sequence.

In theory, only escapes like `\'` `\n` `\\` are strictly necessary, and no
bytes need to be hex-escaped.  But that strategy would defeat the purpose of
QSN for many applications, like printing filenames in a terminal.

### List of Syntax Errors

QSN decoders must enforce (at least) these syntax errors:

- Literal newline or tab in a string.  Should be `\t` or `\n`.  (The lack of
  literal tabs and newlines is essential for [QTT][].)
- Invalid character escape, e.g. `\z`
- Invalid hex escape, e.g. `\xgg`
- Invalid unicode escape, e.g. `\u{123` (incomplete)

Separate messages aren't required for each error; the only requirement is that
they not accept these sequences.

## Reference Implementation in Oil

- Oil's **encoder** is in [qsn_/qsn.py]($oils-src), including the state machine
  for the UTF-8 strategies.
- The **decoder** has a lexer in [frontend/lexer_def.py]($oils-src), and a
  "parser" / validator in [qsn_/qsn_native.py]($oils-src).  (Note that QSN is a
  [regular language]($xref:regular-language)).

The encoder has options to emit shell-compatible strings, which you probably
**don't need**.  That is, C-escaped strings in bash look `$'like this\n'`.

A **subset** of QSN is compatible with this syntax.  Example:

    $'\x01\n'  # A valid bash string.  Removing $ makes it valid QSN.

Something like `$'\0065'` is never emitted, because QSN doesn't contain octal
escapes.  It can be encoded  with hex or character escapes.

## Appendices

### Design Notes

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

### Related Links

- [GNU Coreutils - Quoting File names][coreutils-quotes].  *Starting with GNU
  coreutils version 8.25 (released Jan. 2016), ls's default output quotes
  filenames with special characters*
- [In-band signaling][in-band] is the fundamental problem with filenames and
terminals.  Code (control codes) and data are intermingled.
- [QTT][] is a cleanup of CSV/TSV, built on top of QSN.

[coreutils-quotes]: https://www.gnu.org/software/coreutils/quotes.html

[in-band]: https://en.wikipedia.org/wiki/In-band_signaling


### `set -x` example

When arguments don't have any spaces, there's no ambiguity:


    $ set -x
    $ echo two args
    + echo two args

Here we need quotes to show that the `argv` array has 3 elements:

    $ set -x
    $ x='a b'
    $ echo "$x" c
    + echo 'a b' c

And we want the trace to fit on a single line, so we print a QSN string with
`\n`:

    $ set -x
    $ x=$'a\nb'
    $ echo "$x" c
    + echo $'a\nb' c

Here's an example with unprintable characters:

    $ set -x
    $ x=$'\e\001'
    $ echo "$x"
    + echo $'\x1b\x01'
