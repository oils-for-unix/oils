---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

OSH Assignment
===

This chapter in the [Oils Reference](index.html) describes OSH assignment.

<div id="toc">
</div>

## Operators

### sh-assign

### sh-append

## Compound Data

### sh-array

Array literals in shell accept any sequence of words, just like a command does:

    ls $mystr "$@" *.py

    # Put it in an array
    a=(ls $mystr "$@" *.py)

In YSH, use [list-literal](chap-expr-lang.html#list-literal).

### sh-assoc

In YSH, use [dict-literal](chap-expr-lang.html#dict-literal).

## Builtins

### local

### export

### unset

### shift

### declare

### typeset

Another name for the [declare](#declare) builtin.
