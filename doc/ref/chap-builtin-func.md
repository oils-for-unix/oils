---
title: Builtin Functions (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **Builtin Functions**

</div>

This chapter describes builtin functions (as opposed to [builtin
commands](chap-builtin-cmd.html).)

<span class="in-progress">(in progress)</span>

<div id="toc">
</div>

## Values

### len()

Returns the

- number of entries in a `List`
- number of pairs in a `Dict`
- number of bytes in a `Str`
  - TODO: `countRunes()` can return the number of UTF-8 encoded code points.

### func/type()

Given an arbitrary value, returns a string representing the value's runtime
type.

For example:

    var d = {'foo': 'bar'}
    var n = 1337

    $ = type(d)
    (Str)    'Dict'

    $ = type(n)
    (Str)    'Int'

Similar names: [type][]

[type]: chap-index.html#type

### repeat()

TODO:

    = repeat('a', 3)
    (Str)   'aaa'

    = repeat(['a'], 3)
    (List)   ['a', 'a', 'a']

Note that list elements are NOT copied.  They are repeated by reference, which
means the List can have aliases.

    = repeat([[42]], 3)
    (List)   [[42], [42], [42]]

Modeled after these Python expressions:

    >>> 'a' * 3
    'aaa'
    >>> ['a'] * 3
    ['a', 'a', 'a']


## Conversions

### bool()

Returns the truth value of its argument. Similar to `bool()` in python, it
returns `false` for:

- `false`, `0`, `0.0`, `''`, `{}`, `[]`, and `null`.

Returns `true` for all other values.

### int()

Given a float, returns the largest integer that is less than its argument (i.e. `floor()`).

    $ = int(1.99)
    (Int)    1

Given a string, `Int()` will attempt to convert the string to a base-10
integer. The base can be overriden by calling with a second argument.

    $ = int('10')
    (Int)   10

    $ = int('10', 2)
    (Int)   2

    ysh$ = Int('foo')
    # fails with an expression error

### float()

Given an integer, returns the corressponding flaoting point representation.

    $ = float(1)
    (Float)   1.0

Given a string, `Float()` will attempt to convert the string to float.

    $ = float('1.23')
    (Float)   1.23

    ysh$ = float('bar')
    # fails with an expression error

### str()

Converts a `Float` or `Int` to a string.

### list()

Given a list, returns a shallow copy of the original.

Given an iterable value (e.g. a range or dictionary), returns a list containing
one element for each item in the original collection.

    $ = list({'a': 1, 'b': 2})
    (List)   ['a', 'b']

    $ = list(1:5)
    (List)   [1, 2, 3, 4, 5]

### dict()

Given a dictionary, returns a shallow copy of the original.

### chr()

(not implemented)

Convert an integer to a Str with the corresponding UTF-8 encoded code point.

Integers in the surrogate range are an error.

    = chr(97)
    (Str)    'a'

    = chr(0x3bc)
    (Str)    'μ'

### ord()

(not implemented)

Convert a single UTF-8 encoded code point to an integer.

    = ord('a')
    (Int)   97

    = ord('μ')
    (Int)   956  # same as 0x3bc

<!-- Do we have character literals like #'a' ?  Or just use strings.  Small
string optimization helps. -->

### runes()

TODO: Explicit iterator over runes.

## Str

### strcmp()

TODO

### split()

TODO

If no argument is passed, splits by whitespace 

<!-- respecting Unicode space? -->

If a delimiter Str with a single byte is given, splits by that byte.

Modes:

- Python-like algorithm
- Is awk any different?
- Split by eggex

### shSplit()

Split a string into a List of strings, using the shell algorithm that respects
`$IFS`.

Prefer `split()` to `shSplit()`.


## List

### join()

Given a List, stringify its items, and join them by a separator.  The default
separator is the empty string.

    var x = ['a', 'b', 'c']

    $ echo $[join(x)]
    abc

    $ echo $[join(x, ' ')]  # optional separator
    a b c


It's also often called with the `=>` chaining operator:

    var items = [1, 2, 3]

    json write (items => join())      # => "123"
    json write (items => join(' '))   # => "1 2 3"
    json write (items => join(', '))  # => "1, 2, 3"


### any()

Returns true if any value in the list is truthy (`x` is truthy if `Bool(x)`
returns true).

If the list is empty, return false.

    = any([])  # => false
    = any([true, false])  # => true
    = any([false, false])  # => false
    = any([false, "foo", false])  # => true

Note, you will need to `source --builtin list.ysh` to use this function.

### all()

Returns true if all values in the list are truthy (`x` is truthy if `Bool(x)`
returns true).

If the list is empty, return true.

    = any([])  # => true
    = any([true, true])  # => true
    = any([false, true])  # => false
    = any(["foo", true, true])  # => true

Note, you will need to `source --builtin list.ysh` to use this function.

## Word

### glob() 

See `glob-pat` topic for syntax.

### maybe()

## Math

### abs()

Compute the absolute (positive) value of a number (float or int).

    = abs(-1)  # => 1
    = abs(0)   # => 0
    = abs(1)   # => 1

Note, you will need to `source --builtin math.ysh` to use this function.

### max()

Compute the maximum of 2 or more values.

`max` takes two different signatures:

  1. `max(a, b)` to return the maximum of `a`, `b`
  2. `max(list)` to return the greatest item in the `list`

For example:

      = max(1, 2)  # => 2
      = max([1, 2, 3])  # => 3

Note, you will need to `source --builtin math.ysh` to use this function.

### min()

Compute the minimum of 2 or more values.

`min` takes two different signatures:

  1. `min(a, b)` to return the minimum of `a`, `b`
  2. `min(list)` to return the least item in the `list`

For example:

    = min(2, 3)  # => 2
    = max([1, 2, 3])  # => 1

Note, you will need to `source --builtin math.ysh` to use this function.

### round()

### sum()

Computes the sum of all elements in the list.

Returns 0 for an empty list.

    = sum([])  # => 0
    = sum([0])  # => 0
    = sum([1, 2, 3])  # => 6

Note, you will need to `source --builtin list.ysh` to use this function.

## Serialize

### toJson()

Convert an object in memory to JSON text:

    $ = toJson({name: "alice"})
    (Str)   '{"name":"alice"}'

Add indentation by passing the `space` param:

    $ = toJson([42], space=2)
    (Str)   "[\n  42\n]"

Similar to `json write (x)`, except the default value of `space` is 0.

See [json-encode-err](chap-errors.html#json-encode-err) for errors.

### fromJson()

Convert JSON text to an object in memory:

    = fromJson('{"name":"alice"}')
    (Dict)   {"name": "alice"}

Similar to `json read <<< '{"name": "alice"}'`.

See [json-decode-err](chap-errors.html#json-decode-err) for errors.

### toJson8()

Like `toJson()`, but it also converts binary data (non-Unicode strings) to
J8-style `b'foo \yff'` strings.

In contrast, `toJson()` will do a lossy conversion with the Unicode replacement
character.

See [json8-encode-err](chap-errors.html#json8-encode-err) for errors.

### fromJson8()

Like `fromJson()`, but it also accepts binary data denoted by J8-style `b'foo
\yff'` strings.

See [json8-decode-err](chap-errors.html#json8-decode-err) for errors.

## Pattern

### `_group()`

Like `Match => group()`, but accesses the global match created by `~`:

    if ('foo42' ~ / d+ /) {
      echo $[_group(0)]  # => 42
    }

### `_start()`

Like `Match => start()`, but accesses the global match created by `~`:

    if ('foo42' ~ / d+ /) {
      echo $[_start(0)]  # => 3
    }

### `_end()`

Like `Match => end()`, but accesses the global match created by `~`:

    if ('foo42' ~ / d+ /) {
      echo $[_end(0)]  # => 5
    }

## Introspection

### `shvarGet()`

Given a variable name, return its value.  It uses the "dynamic scope" rule,
which looks up the stack for a variable.

It's meant to be used with `shvar`:

    proc proc1 {
      shvar PATH=/tmp {  # temporarily set PATH in this stack frame
        my-proc
      }

      proc2
    }

    proc proc2 {
      proc3
    }

    proc proc3 {
      var path = shvarGet('PATH')  # Look up the stack (dynamic scoping)
      echo $path  # => /tmp
    }

    proc1

Note that `shvar` is usually for string variables, and is analogous to `shopt`
for "booleans".

If the variable isn't defined, `shvarGet()` returns `null`.  So there's no way
to distinguish an undefined variable from one that's `null`.

### `getVar()`

Given a variable name, return its value.

    $ var x = 42
    $ echo $[getVar('x')]
    42

The variable may be local or global.  (Compare with `shvarGet()`.) the "dynamic
scope" rule.)

If the variable isn't defined, `getVar()` returns `null`.  So there's no way to
distinguish an undefined variable from one that's `null`.

### `evalExpr()`

Given a an expression quotation, evaluate it and return its value:

    $ var expr = ^[1 + 2]  

    $ = evalExpr(expr)
    3

## Hay Config

### parseHay()

### evalHay()


## Hashing

### sha1dc()

Git's algorithm.

### sha256()


<!--

### Better Syntax

These functions give better syntax to existing shell constructs.

- `shQuote()` for `printf %q` and `${x@Q}`
- `trimLeft()` for `${x#prefix}` and  `${x##prefix}`
- `trimRight()` for `${x%suffix}` and  `${x%%suffix}` 
- `trimLeftGlob()` and `trimRightGlob()` for slow, legacy glob
- `upper()` for `${x^^}`
- `lower()` for `${x,,}`
- `strftime()`: hidden in `printf`

-->
