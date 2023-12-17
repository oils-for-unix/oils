---
default_highlighter: oils-sh
in_progress: true
---

YSH Regex API - A Mix of Python and Perl/Awk
============================================

TODO:

<!--
- Make these work:
  - [`_group()`]($help-topic:_group)
  - [`Match => group()`]($help-topic:group)
  - [`Str => search()`]($help-topic:search)
  - [`Str => leftMatch()`]($help-topic:leftMatch)
-->

Mechanisms

- Awk and Perl-like with ~ operator
  - `_group() _start() _end()` - like Python
- Python-like except on `Str`
  - `Str => search()`
  - `Str => leftMatch()` for lexers
  - note that it's consistent with find() consistency
  - TODO: should accept raw ERE string too
- TODO: replace() and unevaluated string literal
  - is `replace()` polymorphic with strings?
  - or maybe `sub()`

- Others can be implemented with search() and leftMatch()
  - `split()` by regex
    - although is our `Str => split()` also polymorphic?
  - `findAll()` or `allMatches()` - in Python this has a weird signature

Related: [Egg Expressions](eggex.html)

## Basic Tests with ~

    var s = 'days 04-01 and 10-31'
    var pat = /<capture d+ as month> '-' <capture d+ as day>/

    if (s ~ pat) {
      echo $[_group(1)]
    }

## More explicit API 

### search()

    var m = 's' => search(pat)
    if (m) {
      echo $[m => group(1)]
    }

### Iterative matching with with leftMatch():

    var s = 'hi 123'
    var lexer = / <capture [a-z]+> | <capture d+> | <capture s+> /
    var pos = 0
    while (true) {
      var m = s => leftMatch(lexer, pos=pos)
      if (not m) {
        break
      }
      if (m => group(1) !== null) {
        echo 'letter'
      elif (m => group(2) !== null) {
        echo 'digit'
      elif (m => group(3) !== null) {
        echo 'space'
      }

      setvar pos = m => end(0)
    }

## Named Captures and Types - like `scanf()`

    var date_pattern = / <capture d+ as month> '-' <capture d+ as day> /

## Summary

Mix Python and Perl.

## Appendix: Still to be implemented

### Substitution

    var new = s => replace(/<capture d+ as month>/, ^"month is $month")
    # (could be stdlib function)

### Slurping all matches, like Python

    var matches = findAll(s, / (d+) '.' (d+) /)
    # (could be stdlib function)

    # s => findAll(pat) => reversed()

### Splitting

    var parts = s => split(/space+/)  # contrast with shSplit()
    # (could be stdlib function)
