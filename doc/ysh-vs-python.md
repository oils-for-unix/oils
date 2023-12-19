---
---

YSH Expressions vs. Python
==========================

The [YSH]($xref) expression language borrows heavily from Python.  In fact, it
literally started with Python's `Grammar/Grammar` file.

This doc describes the differences, which may help Python users learn YSH.

If you don't know Python, [A Tour of YSH](ysh-tour.html) explains the language
from the clean-slate perspective.

(TODO: A separate doc could compare commands/statements like `for` and `if`.)

<div id="toc">
</div>

## Background

YSH has dynamic types, much like Python.  These are the main **data** types:

    Null Bool Int Float List Dict

Quick example:

    var x = null
    var y = f(true, 42, 3.14)
    var z = [5, 6, {name: 'bob'}]

## Literals

Every data type can be written as a literal.  Literals generally look like
Python, so this section describes what's the same, and what's changed /  added
/ and removed.

### Like Python: numbers and lists

- Integers: `123`, `1_000_000`, `0b1100_0010`, `0o755`, `0xff`
- Floats: `1.023e6`
- Lists: `['pea', 'nut']`
  - TODO: we want Python-like list comprehensions

### Changed: booleans, strings, dicts

- Atoms are `true`, `false`, and `null` (like JavaScript) rather than `True`,
  `False`, and `None` (like Python).
  - In YSH, we use capital letters for types like `Int`.

- String literals are like **shell** string literals, not like Python.
  - Double Quoted: `"hello $name"`
  - Single quoted: `r'c:\Program Files\'` 
  - C-style: `$'line\n'` (TODO: change to J8 Notation)
    - Unicode literals are `\u{3bc}` instead of `\u03bc` and `\U000003bc`

- Dicts use **JavaScript** syntax, not Python syntax.
  - Unquoted keys: `{age: 42}`
  - Bracketed keys: `{[myvar + 1]: 'value'}`
  - "Punning": `{age}`

### Added

- Shell-like list literals: `:| pea nut |` is equivalent to `['pea', 'nut']`

- "Quotation" types for unevaluated code:
  - Command / block `^(ls | wc -l)`
  - Unevaluated expression `^[1 + a[i] + f(x)]`

- Units on number constants like `100 MiB` (reserved, not implemented)

<!--
- Character literals are **integers**
  - Unicode `\u{03bc}`
  - Backslash: `\n`  `\\`  `\'`
  - Pound `#'a'`
- `:symbol` (could be used as interned strings)
-->

### Omitted

- YSH has no tuples, only lists.
- No lambdas (function literals returning an expression)
- No closures, or scope declarations like `global` and `nonlocal`.  (We would
  prefer objects over closures.)
- No iterators.
  - Instead we have for loop that works on lists and dicts.
  - It flexibly accepts up to 3 loop variables, taking the place of Python's
    `enumerate()`, `keys()`, `values()`, and `items()`.

## Operators

Like literals, YSH operators resemble Python operators.  The expression `42 +
a[i]` means the same thing in both languages.

This section describes what's the same, and what's changed / added / removed.

### Note: YSH Does Less Operator Overloading

YSH doesn't overload operators as much because it often does automatic
`Str` &harr; `Int` conversions (like Awk):

- `a + b` is for addition, while `a ++ b` is for concatenation.

- `a < b` does numeric comparison, not lexicographical comparison of strings.
  - (We should add `strcmp()` for strings.)

### Like Python

- Arithmetic `+ - * /` and comparison `< > <= =>`.  They also convert strings
  to integers or floats.  Examples:
  - `'22' < '3'` is true because `22 < 3` is true.
  - `'3.1' <= '3.14'` is true because `3.1 <= 3.14` is true.

- Integer arithmetic: `//` integer division, `%` modulus, `**` exponentiation.
  - They also convert strings to integers (but not floats).

- Bitwise `& | ~ ^ << >>`

- Logical `and or not`

- Ternary `0 if cond else 1`

- Slicing: `s[i:j]` evaluates to a string

- Membership `in`, `not in`

- Identity `is`, `is not`

- Function Call: `f(x, y)`

### Changed

- Equality is `=== !==`, because we also have `~==`.
- String Concatenation is `++`, not `+`.  Again, `+` is always addition.
- Splat operator is `...` not `*`: `f(...myargs)`.

### Added

- Eggex match `s ~ /d+/`
- Glob match `s ~~ '*.py'`
- Approximate Equality `42 ~== '42'`
- YSH sigils: `$` and `@`
- `mydict.key` as an alias for `mydict['key']`

### Omitted

- No string formatting with `%`.  Use `${x %.3f}` instead. (unimplemented)
- No `@` for matrix multiply.
- I removed slice step syntax `1:5:2` because `0::2` could conflict with
  `module::name` (could be restored).

## Syntax Compared With JavaScript

This section may be useful if yo know JavaScript.

- YSH uses `===` and `~==` for exact and type-converting equality, while JS
  uses `===` and `==`.

- Expressions are more like Python:
  - YSH expressions use `and or not` while JS uses `&& || !`.  In shell, `&& ||
    !` are already used in the command language (but they're somewhat less
    important than in YSH).
  - The YSH ternary operator is `0 if cond else 1`, while in JS it's `cond ? 0 :
    1`.
  - Operator precedence rules are slightly different, but still C-like.  They
    follow Python's grammar.

- Same differences as above, versus Python:
  - `s ++ t` for string concatenation rather than `s + t`
  - Shell string literals rather than JS string literals

## Semantics Compared

The runtime behavior of YSH is also similar to Python and JavaScript.

### Versus Python

- `Bool` and `Int` are totally separate types.  YSH is like JavaScript, where
  they aren't equal: `true !== 1`.  In Python, they are equal: `True == 1`.

- Strings are bytes, which may UTF-8 encoded, like Go.  (In Python 3, strings
  are sequences of code points, which are roughly integers up to
  2<sup>21</sup>.)

- We avoid operators that cause "accidentally quadratic" behavior.
  - No `in` on `List`, since that's a linear search.  Only `in` on `Dict`.
  - The're not `++=` operator on strings.

<!-- TODO: "N ways to concat strings " -->

### Versus JavaScript

- Strings are bytes, which may UTF-8 encoded, like Go.  (In 
  JavaScript are sequences of UTF-16 code units, which are roughly integers up
  to 2<sup>16</sup>.)
- Undefined variables result in a fatal error like Python, not a silently
  propagating `undefined` like JavaScript.


