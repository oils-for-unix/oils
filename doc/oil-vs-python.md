---
in_progress: true
---

Oil Expressions vs. Python
==========================

Oil's expression language borrows heavily from Python.  In fact, it literally
started with Python's `Grammar/Grammar` file.

This doc describes some differences, which may help Python users learn Oil.

If you don't know Python, see [A Tour of the Oil
Language](oil-language-tour.html).

<div id="toc">
</div>

## Literals for Data Types

- String literals are like **shell** string literals, not like Python.
  - Single quoted - `r'c:\Program Files\'` or `$'line\n'`.
  - Double Quoted
  - Unicode literals are `\u{3bc}` instead of `\u03bc` and `\U000003bc`
- Dicts: come from JavaScript, with unquoted keys, and "punning".
- Lists: In addition to Python-like literals `['pea', 'nut']`, there are
  shell-like literals `%(pea nut)`.
- Booleans / null: `true`, `false`, and `null` are preferred, but `True`,
  `False`, and `None` are accepted for compatibility.
- Tuples (TODO): Does Oil have true tuples?
  - Singleton tuples like `42,` are disallowed, in favor of the more explicit
    `tup(42)`.

Other literals like ints and floats are the same as in Python.

### New Literal Syntax

- `%symbol` (used in eggex now, but could also be used as interned strings)
- Raw character literals like `\n` and `\u{03bc}`, and also `#'a'`
- Unevaluated expressions
  - Block `^(ls | wc -l)`
  - Unevaluated expression: `^[1 + a[i] + f(x)]`
  - Arg list: `^{42, verbose = true}`

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

Other:

- I removed the `1:5:2` syntax because `0::2` conflicts with `module::name`.
  This might have been unnecessary.

### New Operators

- `mydict->key` as an alias for `mydict['key']`
- `++` mentioned above
- Pattern Matching
  - Egg expressions and the `~` operator rather than the `re` module.
  - The `~~` glob match operator

### Not Supported

- No string formatting with `%`.  Use `${x %.3f}` instead.
- No `@` for matrix multiply.

## Semantic Differences

- Iterating over a string yields code points, not one-character strings.
  - `s[i]` returns an integer code point ("rune").
  - TODO: maybe this should be `runeAt()` and `byteAt()`?
- No "accidentally quadratic"
  - No `in` for array/list membership.  Only dict membership.
  - The `++=` operator on strings doesn't exist
- Bools and integers are totally separate types.  Oil is like JavaScript, where
  they aren't equal: `true !== 1`.  In Python, they are equal: `True == 1`.

## Related Links

- [Issue 835: Make expression language compatible with Python](https://github.com/oilshell/oil/issues/835)

