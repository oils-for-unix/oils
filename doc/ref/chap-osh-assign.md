---
title: OSH Assignment (Oils Reference)
all_docs_url: ..
body_css_class: width40
default_highlighter: oils-sh
preserve_anchor_case: yes
---

<div class="doc-ref-header">

[Oils Reference](index.html) &mdash;
Chapter **OSH Assignment**

</div>

This chapter describes OSH assignment, which looks like `x=value`.

<span class="in-progress">(in progress)</span>

<div id="dense-toc">
</div>

## Operators

### sh-assign

### sh-append

## Compound Assignment

### sh-init-list

Indexed and associative arrays may be initialized by an assignment of an
initializer list.

    arr=(1 2 3 4)
    dict=([apple]=red [banana]=yellow [orange]=orange)

An initializer list does *NOT* provide a new value that will be assigned to the
LHS of the assignment.  The initializer list is rather considered *a set of
instructions to modify the existing value of the LHS*.

An initializer list has the following form: `(<words>...)`, where each word has
one of the following forms:

- `[<key>]=<value>` ... This assigns `<value>` to an element of the LHS
  specified by `<key>`.  The `<value>` is not subject to word splitting and
  pathname expansions as if it is the RHS of an assignment.
- `[<key>]+=<value>` ... This appends `<value>` to an element of the LHS
  specified by `<key>`.  If the corresponding element does not exist, it simply
  assigns `<value>` to a new element associated with `<key>`.  The `<value>` is
  not subject to word splitting and pathname expansions.
- `<value>` ... If the word does not have the above two forms, it is considered
  a normal word.  In this case, this assigns `<value>` to the *next* element,
  where the next element is determined by the LHS.  Unlike the previous two
  forms, the `<value>` is subject to word splitting and pathname expansions as
  if it is a normal argument to a command.

The above three forms can be mixed within one initializer list, though there
may be additional limitations depending on the type of the LHS of the
assignment.

When the assignment is performed with `=`, the content of the LHS value is
cleared before starting the modifications.  When the assignment is performed
with `+=`, the modification is performed on the existing content of the LHS
value.

The details of the actual modification depends on the type of the LHS:

- When the LHS variable is unset, the assignment creates an empty indexed array
  and apply the initializer list to the created array (see
  [sh-array](#sh-array)).
- When the LHS is a scalar string, the assignment promotes the string to an
  indexed array with a single element at index 0 and applies the initializer
  list to the array (see [sh-array](#sh-array)).
- When the LHS is an indexed or associative arrays, the initializer list is
  applied to the original array following [sh-array](#sh-array) (for an indexed
  array) or [sh-assoc](#sh-assoc) (for an assoative array).
- Otherwise, it is an error.

### sh-array

When an initializer list is assigned to an indexed array, the values will be
set to the elements of the array.  When an initializer word has `<key>`, an
arithmetic evaluation is applied to `<key>` to obtain the index in `BigInt`.
The modification is performed on the element specified by the index.  When an
initializer word does not have `<key>`, the modifcation will be performed on
the element whose index is largen by one than the element modified by the
previous initializer word.

For example, one may store any sequence of words, just like a command does:

    ls $mystr "$@" *.py

    # Put it in an array
    a=(ls $mystr "$@" *.py)

Their type is [BashArray][].

In YSH, use a [list-literal][] to create a [List][] instance.

[BashArray]: chap-type-method.html#BashArray

[List]: chap-type-method.html#List
[list-literal]: chap-expr-lang.html#list-literal


### sh-assoc

When an initializer list is assigned to an associative array (which maps
strings to strings), the values will be set to the elements of the array.  A
word in the initializer list must be the forms `[<key>]=<value>` or
`[<key>]=<value>`.

For example, an associative array can be initialized in the following way:

    declare -A assoc=(['k']=v ['k2']=v2)

Their type is [BashAssoc][].

In YSH, use a [dict-literal][] to create a [Dict][] instance.

[BashAssoc]: chap-type-method.html#BashAssoc

[Dict]: chap-type-method.html#Dict
[dict-literal]: chap-expr-lang.html#dict-literal

## Builtins

### local

### readonly

### export

### unset

### shift

### declare

### typeset

Another name for the [declare](#declare) builtin.
