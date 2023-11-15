---
in_progress: yes
---

Solutions to the Framing Problem
================================

YSH is a shell that lets you write correct programs.  Programs often parse
multiple records or strings sent over a pipe, i.e. the "framing problem".
(This terminology is borrowed from network engineering.)

YSH provides a few solutions for that, and each solution is useful in certain
contexts.

<div id="toc">
</div>

## Delimiter Based Solutions

### Newline as Delimiter

The traditional Unix solution.  It doesn't work when the payload contains
newlines.

Note that Unix filenames, `argv` entries, and `environ` entries can all
contain newlines, but not `NUL` (`\0`).

### NUL as delimiter: `read -0`

So naturally we also support the format that `find -print0` emits, and
`xargs -0` consumes.

## Solutions That Can Express Arbitrary Bytes

### Quoting / Escaping Special characters: [QSN][]

QSN uses backslash escapes like `\n`, `\x00`, and `\u{3bc}` to express
arbitrary bytes (and characters).

### Length-Prefixed: Netstrings

TODO: Implement this.

Like [QSN][], this format is "8-bit clean", but:

- A netstring encoder is easier to write than a QSN encoder.  This may be
  useful if you don't have a library handy.
- It's more efficient to decode, in theory.

However, the encoded output may contain binary data, which is hard to view in a
terminal.

[QSN]: qsn.html

