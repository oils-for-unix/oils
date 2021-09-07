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

### Same as Python

- Integers: `123`, `1_000_000`, `0b1100_0010`, `0o755`, `0xff`
- Floats: `1.023e6` (not in V1 of Oil)
- Lists: `['pea', 'nut']`

### Changed

- Booleans and null: `true`, `false`, and `null` are preferred, but `True`,
  `False`, and `None` are accepted for compatibility.
- String literals are like **shell** string literals, not like Python.
  - Double Quoted: `"hello $name"`
  - Single quoted: `r'c:\Program Files\'` 
  - C-style: `$'line\n'`.
    - Unicode literals are `\u{3bc}` instead of `\u03bc` and `\U000003bc`
- Dicts: use **JavaScript** syntax, not Python
  - Unquoted keys: `{age: 42}`
  - Bracketed keys: `{[myvar + 1]: 'value'}
  - "Punning": `{age}`

### New

- Character literals are **integers**
  - Unicode `\u{03bc}`
  - Backslash: `\n`  `\\`  `\'`
  - Pound `#'a'`
- `%symbol` (used in eggex now, but could also be used as interned strings)
- Shell-like list literals: `%(pea nut)` is equivalent to `['pea', 'nut']`
- Unevaluated expressions
  - Block `^(ls | wc -l)`
  - Unevaluated expression: `^[1 + a[i] + f(x)]`
  - Arg list: `^{42, verbose = true}`

### Removed

- No tuple type for now.  We might want Go-like multiple return values.

<!--
- Tuples (TODO): Does Oil have true tuples?
  - Singleton tuples like `42,` are disallowed, in favor of the more explicit
    `tup(42)`.
-->

## Operators

### Same as Python

- Arithmetic `+ - * / **`
- Comparison `< > <= =>`
- Bitwise `& | ~ ^`
- Logical `and or not`
- Ternary `0 if true else 1`
- Indexing: `s[i]` evaluates to an integer?
- Slicing: `s[i:j]` evaluates to a string
- Equality `== != in  not in`
- Function Call: `f(x, y)`
  - What about splat `*` and `**`?

### Changed

- String Concenation: `++` (not `+`, which is always addition)

### New

- Regex match: `s ~ /d+/`
- Glob match `s ~~ '*.py'`
- Approximate Equality `42 ~== '42'`
- Oil sigils: `$` and `@`
- `mydict->key` as an alias for `mydict['key']`

### Removed

- I removed slice step syntax `1:5:2` because `0::2` conflicts with
  `module::name`.  This was only necessary for Tea, not Oil.
- No string formatting with `%`.  Use `${x %.3f}` instead.
- No `@` for matrix multiply.

<!--
Do we need `is` and `is not` for identity?
-->

### Notes

Oil doesn't overload operators as much, and does string <-> int conversion:

- `a + b` is for addition, while `a ++ b` is for concatenation.
- `a < b` does numeric comparison (with conversion).  `cmp()` could be for
  strings.

## Semantic Differences

- Iterating over a string yields code points, not one-character strings.
  - `s[i]` returns an integer code point ("rune").
  - TODO: maybe this should be `runeAt()` and `byteAt()`?
- No "accidentally quadratic"
  - No `in` for array/list membership.  Only dict membership.
  - The `++=` operator on strings doesn't exist.
- Bools and integers are totally separate types.  Oil is like JavaScript, where
  they aren't equal: `true !== 1`.  In Python, they are equal: `True == 1`.

## Related Links

- [Issue 835: Make expression language compatible with Python](https://github.com/oilshell/oil/issues/835)

## TODO

- Test out `%symbol`
- `100 MiB`?  This should be multiplication?
- All the unevaluated expressions


