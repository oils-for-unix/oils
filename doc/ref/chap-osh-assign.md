---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oil-sh
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

In Oil, use [oil-array]($oil-help).

### sh-assoc

In Oil, use [oil-dict]($oil-help).

## Builtins

### local

### export

### unset

### shift

### declare

### typeset

Alias for [declare]($osh-help).
