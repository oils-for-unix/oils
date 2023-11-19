---
in_progress: true
---

YSH Expressions vs. Python
==========================

The [YSH]($xref) expression language borrows heavily from Python.  In fact, it
literally started with Python's `Grammar/Grammar` file.

This doc describes some differences, which may help Python users learn YSH.

If you don't know Python, see [A Tour of YSH](ysh-tour.html).

<div id="toc">
</div>

## Literals for Data Types

### Literals Like Python: numbers and lists

- Integers: `123`, `1_000_000`, `0b1100_0010`, `0o755`, `0xff`
- Floats: `1.023e6`
- Lists: `['pea', 'nut']`

<!--
TODO: Add list comprehensions back
-->

### Literals Changed: booleans, strings, dicts

- `true`, `false`, and `null` (like JavaScript) rather than `True`, `False`,
  and `None` (like Python).  In YSH, types are spelled with capital letters.
- String literals are like **shell** string literals, not like Python.
  - Double Quoted: `"hello $name"`
  - Single quoted: `r'c:\Program Files\'` 
  - C-style: `$'line\n'` (TODO: change to J8 Notation)
    - Unicode literals are `\u{3bc}` instead of `\u03bc` and `\U000003bc`
- Dicts: use **JavaScript** syntax, not Python
  - Unquoted keys: `{age: 42}`
  - Bracketed keys: `{[myvar + 1]: 'value'}`
  - "Punning": `{age}`

### Literals Added

- Shell-like list literals: `:| pea nut |` is equivalent to `['pea', 'nut']`
- Unevaluated expressions
  - Block `^(ls | wc -l)`
  - Unevaluated expression: `^[1 + a[i] + f(x)]`
- Units on number constants like `100 MiB` (not implemented)

<!--
- Character literals are **integers**
  - Unicode `\u{03bc}`
  - Backslash: `\n`  `\\`  `\'`
  - Pound `#'a'`
- `:symbol` (could be used as interned strings)
-->

### Literals Omitted

- YSH has no tuples, only lists.
- Lambdas.  Functions are often external and don't have lexical scope.
- Iterators.
  - Instead we have for loop that works on lists and dicts.
  - It flexibly accepts up to 3 loop variables, taking the place of Python's
    `enumerate()`, `keys()`, `values()`, and `items()`.

## Operators

### Note: YSH Does Less Operator Overloading

YSH doesn't overload operators as much because it often does automatic string
<-> int conversion (like Awk):

- `a + b` is for addition, while `a ++ b` is for concatenation.
- `a < b` does numeric comparison, not lexicographical comparison of strings.
  - (We should add `cmp()` for strings.)

### Operators Like Python

- Arithmetic `+ - * /` and comparison `< > <= =>`.  They also convert strings
  to integers or floats.  Examples:
  - `'22' < '3'` is true because `22 < 3` is true.
  - `'3.1' <= '3.14'` is true because `3.1 <= 3.14` is true.
- Integer arithmetic: `//` integer division, `%` modulus, `**` exponentiation.
  They also convert strings to integers (not floats).
- Bitwise `& | ~ ^ << >>`
- Logical `and or not`
- Ternary `0 if cond else 1`
- Slicing: `s[i:j]` evaluates to a string
- Membership `in`, `not in`
- Ideneity `is`, `is not`
- Function Call: `f(x, y)`

### Operators Changed

- Equality `=== !==` because we also have `~==`
- String Concatenation: `++` (not `+`, which is always addition)
- Splat operator is `...` not `*`: `f(...myargs)`

### Operators Added

- Eggex match `s ~ /d+/`
- Glob match `s ~~ '*.py'`
- Approximate Equality `42 ~== '42'`
- YSH sigils: `$` and `@`
- `mydict.key` as an alias for `mydict['key']`

### Operators Removed

- No string formatting with `%`.  Use `${x %.3f}` instead. (unimplemented)
- No `@` for matrix multiply.
- I removed slice step syntax `1:5:2` because `0::2` could conflict with
  `module::name` (could be restored).

## YSH vs. JavaScript

- YSH uses `===` and `~==` for exact and type-converting equality, while JS uses
  `===` and `==`.
- Where YSH is consistent with Python
  - YSH expressions use `and or not` while JS uses `&& || !`.  In shell, `&& ||
    !` are already used in the command language (but they're somewhat less
    important than in YSH).
  - The YSH ternary operator is `0 if cond else 1`, while in JS it's `cond ? 0 :
    1`.
  - Operator precedence rules are slightly different, but still C-like.  They
    follow Python's grammar.
- Same differences as YSH vs. Python
  - `s ++ t` for string concatenation rather than `s + t`
  - Shell string literals rather than JS string literals

## Semantics

YSH syntax is a mix of Python and JavaScript, but the **semantics** are
closer to Python.

### Differences vs. Python

- Bools and integers are totally separate types.  YSH is like JavaScript, where
  they aren't equal: `true !== 1`.  In Python, they are equal: `True == 1`.
- No "accidentally quadratic"
  - No `in` for array/list membership.  Only dict membership.
  - The `++=` operator on strings doesn't exist.

