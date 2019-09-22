Egg Expressions (Oil Regexes)
=============================

## Intro

Oil has a new but familiar regex syntax called "Egg Expressions".  Why?

- It lets you compose and reuse regexes.  Breaking regexes up makes them more
  readable and testable.
- String literals are **quoted**, and operators aren't.  This removes many
  tortured parts of regex syntax.
  - For example, the `^` character no longer means three different things; `\`
    and `? + *` no longer mean multiple things; etc.
- It's designed to compile to any regex dialect in theory.  In practice, it
  integrates well with tools that use the ERE syntax:
  - `egrep` (`grep -E`)
  - awk
  - GNU sed `--regexp-extended`
  - PCRE syntax is the second most important target.
- It's shorter and more familiar than ERE syntax, which is what bash already
  uses.
- It's statically parsed in Oil.  You can get syntax errors at parse time,
  whereas if you embed a regex in a string, you can't.
  - The regex is part of the "LST", which means you can do linting, formatting,
    and refactoring on regexes, just like any other type of code.

TODO: This should be in a compact cheat-sheet format.

### Example

Here's how you use them in Oil:

    var D = / digit{1,3} /  # Reuse this subpattern
    var ip_address = / @D '.' @D '.' @D '.' @D /
    echo $ip_address
    egrep $ip_address foo.txt

TODO: inlining in the command language:

    egrep $/d+/ foo.txt

### Philosophy

- Expresses a superset of POSIX and Perl.
- 1:1 dumb translation.  We're not doing any transformations that rely on
  understanding the semantics of regexes.  Regex implementations have many
  corner cases and incompatibilities, with regard to Unicode, `NUL` bytes, etc.

## The Expression language

Regexes.

### Compound Structures

#### Sequences, Alternation

- `x y` matches `x` and `y` in sequence
- `x | y` matches `x` or `y` (`x or y` also accepted)

#### Repetition

Repetition is just like POSIX ERE or Perl:

- `x?`, `x+`, `x*` 
- `x{3}`, `x{1,3}`

Reserved space:

- lazy/non-greedy: `x{L +}`, `x{L 3,4}`
- possessive: `x{P +}`, `x{P 3,4}`

#### Negation

Both named char classes and char class literals can be negated:

    / ~digit /
    / [ ~digit ] /
    / ~[ a-z ] /

    # Does this work?
    / ~[ ~digit ] /


#### Splicing

New in EggEx!  You can reuse patterns.  Like re2c /lex.


    var D = / digit{1,3} /
    var IP = / @D '.' @D '.' @D '.' @D /
    echo $IP


#### Grouping, Capturing

- `(digit{4} as year Int)`
- `:(digit+)`  # not captured

See note below: POSIX ERE has no non-capturing groups.

### Character Class Literals

Example:

    [ a-f 'A'-'F' \x01 \n \\ \' \" \0 ]

Terms:

- ranges: `a-f` or `'A' - 'F'`
- character literals: `\n`, `\x01`, etc.
- character sets specified as strings:
  - `'abc'`
  - `"xyz"`
  - `$mychars`
  - `${otherchars}`

### Primitives

- Classes are unadorned: `w` `d` `alnum`
  - Perl
  - POSIX
- Zero-width assertions are `%start`
- Literals:
  - `'abc'`
  - `"xyz"`
  - `$mychars`
  - `${otherchars}`

- Legacy:
  - `. ^ $`

### Flags and Predispositions

    / digit+ ; ignorecase /

    / digit+ ; ignorecase ; ERE /

    / digit+ ;; ERE /


### Backtracking Constructs (Discouraged)

For PCRE, etc.

### Multiline Syntax

Not implemented:

    var x = ///
      digit{4}     # year e.g. 2001
      '-'
      digit{2}   # month e.g. 06
      '-'
      digit{2}   # day e.g. 31
    ///


### Language Reference

- See Oil Grammar
- See frontend/syntax.asdl

## The Oil API

TODO:

    if (x ~ pat) {
    }

Link?

## Style Notes

### Use Character Literals Rather than C-Escaped Strings

NO:

    / c'foo\tbar' /   # Match 7 characters including a tab, but it's hard to read
    / r'foo\tbar' /   # The string must contain 8 chars including '\' and 't'

YES:

    # Instead, Take advantage of char literals and implicit regex concatenation
    / 'foo' \t 'bar' /
    / 'foo' \\ 'tbar' /



## ERE Limitations

### Surround Repeated Strings with a Capturing Group ()

NO:

    'foo'+ 
    $string_with_many_chars+

YES:

    ('foo')+
    ($string_with_many_chars)+

### Unicode Character Literals Can't Be in Char Class Literals

NO:

    # ERE can't represent this, and 2 byte utf-8 encoding could be confused
    with 2 bytes.
    / [ \u0100 ] /

YES:

    # This is accepted -- it's clear it matches one of two bytes.
    / [ \x61 \xFF ] /

### ] is Confusing in Char Class Literals

ERE wants it like this:

    []abc]

These don't work:

    [abc\]]
    [abc]]

So in Oil you have to write it like this:

YES:

    / [ ']' 'abc'] /

NO:

    / [ 'abc' ']' ] /
    / [ 'abc]' ] /

Since we do a dumb syntactic translation, we can't detect whether it's on the
front or back.  You have to put it in the right place.


## Critiques

### Of Existing Regex Syntax

- `^` could mean:
  - start of the string
  - negated character class in `[^abc]`
  - literal `^` in `[abc^]`
- `\` doesn't mean so many different things
  - character classes like `\w` or `\d`
  - Zero-width assertions like `\b`
  - Escaped characters like `\n`
  - Quoted characters like `\+`
- `?` could mean
  - optional: `a?`
  - lazy match: `a+?`
  - some other kind of grouping:
    - `(?P<named>\d+)`
    - `(?:noncapturing)`

In Oil, each construct has a distinct syntax.


### Oil is Shorter than Bash

    if [[ $x =~ '[[:digit:]]+' ]]; then
      echo 'x looks like a number
    fi

    if (x ~ /digit+/) {
      echo 'x looks like a number'
    }


### And Perl

It's also shorter than Perl because we can write

    x ~ /d+/

rather than:

    $x =~ /\d+/

The Perl expression has three more puncutation characters.

## TODO

multiline syntax: top one in terms of usefulness

    var x = ///
      abc   # TODO: comments
      a+
    ///

Regex FLAGS 

    $/ d+ ; ignorecase ~multiline/
    $/ d+ ; i ~m/

Disposition

    $/ d+ ; i m ; PCRE/     %ERE, %PCRE, %Python

    echo $/ d+ ; ignorecase ; ERE/    # prints [[:digit:]]
    echo $/ d+ ; ignorecase ; perl/   # prints \d+
    echo $/ d+ ;; python/             # prints \d+

Inline syntax:

  grep -P $/d+ ;; perl/ f


Zero-width asertions

- %start_word %end_word  for < and >

API:

- `while` or `for` loop, saving state (like "sticky" bit)
- `sub()` (and `=>` syntax)
- `findall()`
- `split()`


Other ideas: either/or syntax

