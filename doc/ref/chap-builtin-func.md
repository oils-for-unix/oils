---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oil-sh
---

Builtin Functions
===

This chapter in the [Oils Reference](index.html) describes builtin functions.

(As opposed to [builtin commands](chap-builtin-cmd.html).

<div id="toc">
</div>

## Values

### len()

### type()

Given an arbitrary value, returns a string representing the value's runtime type.

For example:

    var d = {'foo': 'bar'}
    var n = 1337

    $ echo $[type(d)]
    Dict

    $ echo $[type(n)]
    Int

## Math

### abs()

### max()

### min()

### round()

### sum()

## Bool()

Returns the truth value of its argument. Similar to `bool()` in python, it returns `false` for `false`, `0`, `0.0`,
`''`, `{}`, `[]`, and `null`.  Returns `true` for all other values.

## Int()

Given a float, returns the largest integer that is less than the given value.

    $ = Int(1.23)
    (Int)    1

Given a string, `Int()` will attempt to convert the string to a base-10 integer. The base can be overriden by calling
with a second argument.


    $ = Int('10')
    (Int)   10

    $ = Int('10', 2)
    (Int)   2

    ysh$ = Int('foo')
    # fails with an expression error

## Float()

Given an integer, returns the corressponding value flaoting point representation.

    $ = Float(1)
    (Float)   1.0

Given a string, `Float()` will attempt to convert the string to float.

    $ = Float('1.23')
    (Float)   1.23

    ysh$ = Float('bar')
    # fails with an expression error

## Str()

Returns its argument if it's a string.

## List()

Given a list, returns a shallow copy of the original.

Given an interable value (e.g. a range or dictionary), returns a list containing one element for each item in the
original colleciton.

    $ = List({'a': 1, 'b': 2})
    (List)   ['a', 'b']

    $ = List(1:5)
    (List)   [1, 2, 3, 4, 5]

## Dict()

Given a dictionary, returns a shallow copy of the original.

## Pattern

### `_match()`

### `_start()`

### `_end()`

## Collections

### len()

- `len(mystr)` is its length in bytes
- `len(myarray)` is the number of elements
- `len(assocarray)` is the number of pairs

## String

### find 

### sub 

### join 

Given an array of strings, returns a string.

    var x = ['a', 'b', 'c']

    $ echo $[join(x)]
    abc

    $ echo $[join(x, ' ')]  # optional delimiter
    a b c

### split

<!--
Note: This is currently SplitForWordEval.  Could expose Python-type splitting?
-->

## Word

<!--
Note: glob() function conflicts with 'glob' language help topic
-->

### maybe

## Arrays

- `index(A, item)` is like the awk function
- `append()` is a more general version of the `append` builtin
- `extend()`

## Assoc Arrays

- `keys()`
- `values()`

## Introspection

### `shvar_get()`

TODO

## Config Gen

### Better Syntax

These functions give better syntax to existing shell constructs.

- `shquote()` for `printf %q` and `${x@Q}`
- `lstrip()` for `${x#prefix}` and  `${x##prefix}`
- `rstrip()` for `${x%suffix}` and  `${x%%suffix}` 
- `lstripglob()` and `rstripglob()` for slow, legacy glob
- `upper()` for `${x^^}`
- `lower()` for `${x,,}`
- `strftime()`: hidden in `printf`


## Codecs

TODO

## Hashing

TODO

