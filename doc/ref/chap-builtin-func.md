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

## Math

### abs()

### max()

### min()

### round()

### sum()

## Int


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

