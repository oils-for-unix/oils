---
default_highlighter: oils-sh
---

YSH Regex API - Convenient and Powerful
=======================================

YSH has [Egg Expressions](eggex.html), a composable and readable syntax for
regular expressions.  You can use *Eggex* with both:

- A convenient Perl-like operator: `'mystr' ~ / [a-z]+/ `
  - access submatches with global `_group()` &nbsp; `_start()` &nbsp; `_end()`

- A powerful Python-like API: `'mystr' => search(/ [a-z]+ /)` and `leftMatch()`
  - access submatches with `Match` object methods `m => group()` &nbsp; `m =>
    start()` &nbsp; `m => end()`

You can also use plain POSIX regular expressions ([ERE]($xref)) instead of
Eggex.

<div id="toc">
</div>

<!--
TODO: need $help-topic shortcut

- [`_group()`]($help-topic:_group)
- [`Match => group()`]($help-topic:group)
- [`Str => search()`]($help-topic:search)
- [`Str => leftMatch()`]($help-topic:leftMatch)
-->

## Perl-Like `~` operator

The `~` operator tests if a string matches a pattern.  The captured groups are
available through "global register" functions starting with `_`.

    var s = 'days 04-01 and 10-31'
    var eggex = /<capture d+ as month> '-' <capture d+ as day>/

    if (s ~ eggex) {
      = _group(1)  # => '04', the first capture
      = _group(2)  # => '01', the second capture

      = _start(1)  # => 5, start index of the first capture
      = _end(1)    # => 7, end index of the first capture
    }

The eggex pattern has **named capture** `as month`, so it's more typical to
write:

    if (s ~ eggex) {
      = _group('month')  # => '04'
      = _group('day')    # => '01'

      = _start('month')  # => 5
      = _end('month')    # => 7
    }

You can test if a string does **not** match a pattern with `!~`:

    if (s !~ / space /) {
      echo 'no whitespace'
    }

The pattern can also be a string, in plain [ERE]($xref) syntax:

    if (s ~ '([[:digit:]]+)') {
      = _group(1)
    }

Help topics:

- [match-ops](ref/chap-expr-lang.html#match-ops)
  - [`_group()`](ref/chap-builtin-func.html#_group)
  - [`_start()`](ref/chap-builtin-func.html#_start)
  - [`_end()`](ref/chap-builtin-func.html#_end)

## Python-like API

### `search()` returns a value.Match object

The `search()` method is like the `~` operator, but it returns either `null` or
a `Match` object.

`Match` objects have `group()`, `start()`, and `end()` methods.

    var m = 's' => search(eggex)
    if (m) {  # test if it  matched
      = m => group('month')  # => '04'
      = m => group('day')    # => '01'
    }

You can search from a given starting position:

    var m = 's' => search(eggex, pos=12)
    if (m) {
      = m => group('month')  # => '10', first month after pos 12
      = m => group('day')    # => '31', first day after pos 12
    }

The `search()` method is a bit like `Str => find()`, which searches for a
substring rather than a pattern.

Help topics:

- [search()](ref/chap-type-method.html#search) for a pattern
  - [Match => group()](ref/chap-type-method.html#group)
  - [Match => start()](ref/chap-type-method.html#start)
  - [Match => end()](ref/chap-type-method.html#end)
- [find()](ref/chap-type-method.html#find) a substring

### `leftMatch()` for Iterative matching / Lexers

The `leftMatch()` method is like `search()`, but the string must match the
pattern at the left-most position.

It's useful for writing iterative lexers.

    var s = 'hi 123'

    var Name  = / <capture [a-z]+ as name> /
    var Num   = / <capture d+ as num> /
    var Space = / <capture s+ as space> /

    # 3 kinds of tokens.
    # (For CapWords variables, splicing @Name doesn't require @.)
    var lexer = / Name | Num | Space /

    var pos = 0  # start at position 0
    while (true) {
      var m = s => leftMatch(lexer, pos=pos)
      if (not m) {
        break
      }
      # Test which subgroup matched
      var id = null
      if (m => group('name') !== null) {
        setvar id = 'name'
      } elif (m => group('num') !== null) {
        setvar id = 'num'
      } elif (m => group('space') !== null) {
        setvar id = 'space'
      }
      # Calculate the token value
      var end_pos = m => end(0)
      var val = s[pos:end_pos]

      echo "Token $id $val"

      setvar pos = end_pos  # Advance position
    }

(YSH `leftMatch()` vs. `search()` is like Python's `re.match()` vs.
`re.search().`)

- Help topic: [leftMatch()](ref/chap-type-method.html#leftMatch)

## More Features

### Named Captures

As noted above, you can name a capture group with say `<capture d+ as month>`,
and access it with either

- `_group('month')` for the global match
- `m => group('month')` when using `Str` methods

### Type Conversion Funcs - A Better `scanf()`

You can also add `: funcName` to convert the captured string to a different
value.

    var pat = / <capture d+ as month: int> /
    if ('10-31' ~ pat) {
      = _group('month')  # the integer 10, not the string '10'
    }

The `func` should accept a string, and return any type of value.

Conversion funcs also work with positional captures: `/<capture d+ : int>/`.

- Help topic: [re-capture](ref/chap-expr-lang.html#re-capture)

### Replacement / Substitution (TODO)

We plan to use unevaluated string literals like `^"hello $1"` ("quotations") as
the replacement object.

This is instead of custom Python's custom language like `'hello \g<1>`.

    # var new = s => replace(/<capture d+ as month>/, ^"month is $month")

- Help topic: [replace()](ref/chap-type-method.html#replace)

<!--

Notes:
- replace() can be for both substring and eggex?
- replace() can also be a func taking a match object?

-->

## Summary

YSH is designed to have the **convenience** of Perl and Awk, and the **power**
of Python and JavaScript.

Eggexes can be composed by *splicing*.  Splicing works on expressions, not
strings.

Replacement will use shell's string literal syntax, rather than a new

printf`-like mini-language.

## Appendix: Python-like wrappers around the API

### Slurping All Matches

Python's `findall()` function can be emulated by using `search()` in a loop,
similar to the lexer example above:

    func findAll(s, pat) {
      var pos = 0
      var result = []
      while (true) {
        var m = s => search(pat, pos=pos)
        if (not m) {
          break
        }
        var left = m => start(0)
        var right = m => end(0)
        call result->append(s[left:right])
        setvar pos = right
      }
      return (result)
    }

    var matches = findAll('days 04-01 and 10-31', / d+ '-' d+ /)
    json write (matches)  # => ['04-01', '10-31']

### Split by Pattern

Python's `re.split()` can also be emulated by using `search()` in a loop.

## Eggex Help Topics

- [re-literal](ref/chap-expr-lang.html#re-literal)
- [re-primitive](ref/chap-expr-lang.html#re-primitive)
- [class-literal](ref/chap-expr-lang.html#class-literal)
- [named-class](ref/chap-expr-lang.html#named-class)
- [re-compound](ref/chap-expr-lang.html#re-compound)
- [re-capture](ref/chap-expr-lang.html#re-capture)
- [re-flags](ref/chap-expr-lang.html#re-flags)

