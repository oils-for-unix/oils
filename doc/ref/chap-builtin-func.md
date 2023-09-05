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

    $ = type(d)
    (Str)    'Dict'

    $ = type(n)
    (Str)    'Int'

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

## Bool()

Returns the truth value of its argument. Similar to `bool()` in python, it returns `false` for `false`, `0`, `0.0`,
`''`, `{}`, `[]`, and `null`.  Returns `true` for all other values.

## Int()

Given a float, returns the largest integer that is less than its argument (i.e. `floor()`).

    $ = Int(1.99)
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

Given an integer, returns the corressponding flaoting point representation.

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

Given an iterable value (e.g. a range or dictionary), returns a list containing one element for each item in the
original collection.

    $ = List({'a': 1, 'b': 2})
    (List)   ['a', 'b']

    $ = List(1:5)
    (List)   [1, 2, 3, 4, 5]

## Dict()

Given a dictionary, returns a shallow copy of the original.

## List

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

