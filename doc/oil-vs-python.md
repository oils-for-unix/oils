---
in_progress: true
---


Oil Expressions vs. Python
==========================

Oil's expression language borrows heavily from Python.

In fact, it literally started with Python's `Grammar/Grammar` file.

<div id="toc">
</div>

## Literal Syntax

- String literals are like shell string literals.
  - Single quoted - `r'c:\Program Files\'` or `$'line\n'`.
  - Double Quoted
  - `\u{3bc}` instead of `\uhhhh` and `\UHHHHHHHH`
- Dicts: come from JavaScript, with unquoted keys, and "punning".
- lists, ints, floats: the same
- Tuples (TODO):
  - Singleton tuples like `42,` are disallowed, in favor of the more explicit
    `tup(42)`.

### New Literals

- Lists with unquoted words: `%(one two three)`
- `%symbol` (used in eggex now, but could also be used as interned strings)
- Raw character literals like `\n` and `\u{03bc}`, and also `#'a'`
- Block `^(ls | wc -l)`
- Unevaluated expression: `^[1 +a[i] + f(x)]`

## Operators

Kinds of of operators:

- Equality `=== ~== in  not in`
- Comparison `< > <= =>`
- Arithmetic `+ -`
- Bitwise `& |`
- Logical `and or`
- Ternary
- Indexing and Slicing
- Function Call
- Other: `++`
- Oil sigils: `$` and `@`

Equality:

- `===` for exact quality?
- `~==` for approximate (numbers and strings)
  - maybe there is no `==`?

Oil doesn't overload operators as much, and does string <-> int conversion:

- `a + b` is for addition, while `a ++ b` is for concatenation.
- `a < b` does numeric comparison (with conversion).  `cmp()` could be for
  strings.

No "accidentally quadratic"

- No `in` for array/list membership.  Only dict membership.
- The `++=` operator on strings doesn't exist

Other:

- I removed the `1:5:2` syntax because `0::2` conflicts with `module::name`.
  This might have been unnecessary.
- Egg expressions and the `~` operator rather than the `re` module.
- The `~~` glob match operator

### New Operators

- `mydict->key` as an alias for `mydict['key']`
- `++` mentioned above

## Semantic Differences

- Iterating over a string yields code points, not one-character strings.
  - `s[i]` returns an integer code point ("rune").
  - TODO: maybe this should be `runeAt()` and `byteAt()`?

## Related Links

- [Issue 835: Make expression language compatible with Python](https://github.com/oilshell/oil/issues/835)

