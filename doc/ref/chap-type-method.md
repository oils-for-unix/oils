---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
---

YSH Types and Methods
===

This chapter in the [Oils Reference](index.html) describes YSH types and methods.

<div id="toc">
</div>

## Null

## Bool

### fromStr

## Int

### fromStr

## Str

### toJ8

## List

### join

Stringify all items in a list and join them by a seperator (default seperator
is the empty string `""`.)

    var items = [1, 2, 3]

    json write (items->join())  # "123"
    json write (items->join(" "))  # "1 2 3"
    json write (items->join(", "))  # "1, 2, 3"

See also: [`join()`](./chap-builtin-func.html#join)

## Dict

