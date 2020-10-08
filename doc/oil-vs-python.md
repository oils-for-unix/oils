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
  - Single quoted - raw or c.
  - Double Quoted
  - `\u{3bc}` instead of `\uhhhh` and `\UHHHHHHHH`
- Singleton tuples like `42,` are disallowed, in favor of the more explicit
  `tup(42)`.
- Dicts: come from JavaScript, with unquoted keys, and "punning".
- lists, ints, floats: the same

Additions:

- Lists with unquoted words: `%(one two three)`

## Operators

Oil doesn't overload operators as much:

- `a + b` is for addition, while `a ++ b` is for concatenation.
- `a < b` is only for numbers.  `cmp()` could be for strings.

No "accidentally quadratic"

- No `in` for array/list membership.  Only dict membership.
- The `++=` operator on strings doesn't exist

Other:

- I removed the `1:5:2` syntax because `0::2` conflicts with `module::name`.
  This might have been unnecessary.
- Egg expressions and `~` rather than the `re` module.


## Semantic Differences

- Iterating over a string yields code points, not one-character strings.
  `s[i]` returns an integer code point ("rune").

## Significant Newlines

- `{}` is different than `[]` and `()`

## Additions

- `d->key`


## Related Links

- [Issue 835: Make expression language compatible with Python](https://github.com/oilshell/oil/issues/835)

