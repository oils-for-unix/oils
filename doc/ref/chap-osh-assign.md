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

When the assignment is performed with `=`, the content of the LHS value is
cleared before starting the modifications.  When the assignment is performed
with `+=`, the modifications are applied to the existing content of the LHS
value.

An initializer list has the following form: `'(' ITEMS* ')'`, where each item
has one of the following forms:

- `[KEY]=VALUE` ... This assigns `VALUE` to an element of the LHS specified by
  `KEY`.  The `VALUE` is not subject to word splitting and pathname expansions
  as if it is the RHS of an assignment.
- `[KEY]+=VALUE` ... This appends `VALUE` to an element of the LHS specified by
  `KEY`.  If the corresponding element does not exist, it simply assigns
  `VALUE` to a new element associated with `KEY`.  The `VALUE` is not subject
  to word splitting and pathname expansions.
- `VALUE` ... If the item does not have the above two forms, it is considered a
  normal word.  In this case, this assigns `VALUE` to the *next* element, where
  the next element is determined by the LHS.  Unlike the previous two forms,
  the `VALUE` is subject to word splitting and pathname expansions as if it is
  a normal argument to a command.

The above three forms can be mixed within one initializer list, though there
may be additional limitations depending on the type of the LHS of the
assignment.

The details of the actual modification depends on the type of the LHS.  The
assignment of an initializer list can be understood in two phases: the type of
the LHS is first adjusted, and then the modifications to the LHS variable are
applied.

In the first phase, the type adjustment is performed in the following way:

- When the LHS variable is unset, the assignment creates an empty indexed array
  (BashArray).  If the
  assignment is performed through an assignment builtin and flag `-A` is
  supplied to the builtin, an empty associative array (BashAssoc) is created
  instead of an empty BashArray.
- When the LHS is a scalar string, the assignment creates a BashArray with one
  element, where the original value is stored at index `0`.  If the assignment
  is performed through an assignment builtin and flag `-A` is supplied to the
  builtin, the assignment creates a BashAssoc with one element, where the
  original value is stored at key `"0"`, instead of a BashArray.  If the
  assignment operator is `+=`, OSH issues an error "Can't append an array to
  string", while Bash is permissive.
- When the LHS is an indexed or associative arrays, the original array is
  directly used for the modification target.  If the
  assignment is performed through an assignment builtin and mismatching flag
  (i.e., `-A` and `-a` for BashArray and BashAssoc, respectively) is supplied,
  OSH discards the original array and creates a new empty BashArray (for flag
  `-a`) or BashAssoc (for flag `-A`), while Bash issues an error preserving the
  original array.
- Otherwise, it is an error.

These rules are summarized in the following table.

<table>

- thead
  - Original LHS type
  - Flags
  - Result
  - Remarks
- tr
  - Undef
  - (none)
  - an empty BashArray
  - <!-- empty -->
- tr
  - <!-- empty -->
  - `-a`
  - an empty BashArray
  - <!-- empty -->
- tr
  - <!-- empty -->
  - `-A`
  - an empty BashAssoc
  - <!-- empty -->
- tr
  - Str
  - (none)
  - BashArray with one element, with the original string at index 0
  - OSH does not accept `+=`, so the element is never used
- tr
  - <!-- empty -->
  - `-a`
  - BashArray with one element, with the original string at index 0
  - OSH does not accept `+=`, so the element is never used
- tr
  - <!-- empty -->
  - `-A`
  - BashAssoc with one element, with the original string at key `"0"`
  - OSH does not accept `+=`, so the element is never used
- tr
  - BashArray
  - (none)
  - the original BashArray
  - <!-- empty -->
- tr
  - <!-- empty -->
  - `-a`
  - the original BashArray
  - <!-- empty -->
- tr
  - <!-- empty -->
  - `-A`
  - N/A
  - Error
- tr
  - BashAssoc
  - (none)
  - the original BashAssoc
  - <!-- empty -->
- tr
  - <!-- empty -->
  - `-a`
  - N/A
  - Error
- tr
  - <!-- empty -->
  - `-A`
  - the original BashAssoc
  - <!-- empty -->
- tr
  - (others)
  - <!-- empty -->
  - N/A
  - Error

</table>

In the second phase, the modifications are applied depending on the result of
the first phase.  When the result is BashArray, see [sh-array](#sh-array).
When the result is BashAssoc, see [sh-assoc](#sh-assoc).

### sh-array

When an initializer list is assigned to [BashArray][], the values will be set
to elements of the array.  For example, one may store any sequence of words,
just like a command does:

    ls $mystr "$@" *.py

    # Put it in an array
    a=(ls $mystr "$@" *.py)

To explain the initialization/mutation in more detail, the array is first
cleared if the assignment operator is `=`.  Then, an element of the array is
modified for each item in the initializer list in order.  The index of the
element to be modified is determined in the following way:

- When the first initializer item does not have `[KEY]=` or `[KEY]+=`, the
  index is the maximum existing index in the array plus one, or `0` if the
  array is empty.
- When the second or later initializer item does not have `[KEY]=` or
  `[KEY]+=`, the index is larger by one than the one modified by the previous
  initializer item.
- When the initializer item has `[KEY]=` or `[KEY]+=`, an arithmetic evaluation
  is applied to `KEY` to obtain the index in `BigInt`

Here are examples:

    declare -a a            # This creates an empty array (OSH)
    declare -a a=()         # This creates an empty array
    declare -a a=(1 2)      # This creates an array with two elements: (1 2)

    k=10
    declare -a a=([k]=v 2)  # This creates a sparse array with two elements,
                            # ([10]=v [11]=2)

    a+=(3 4)                # This appends two values to the existing array:
                            # ([10]=v [11]=2 [12]=3 [13]=4)
    a+=([k]=5 6)            # This overwrites two elements in the existing
                            # array: ([10]=5 [11]=6 [12]=3 [13]=4)

In YSH, use a [list-literal][] to create a [List][] instance.

[BashArray]: chap-type-method.html#BashArray

[List]: chap-type-method.html#List
[list-literal]: chap-expr-lang.html#list-literal


### sh-assoc

When an initializer list is assigned to [BashAssoc][], an associative array
mapping a string into another string, the values will be set to elements of the
associative array.  For example, an associative array can be initialized in the
following way:

    declare -A assoc=(['k']=v ['k2']=v2)

The initialization/mutation of BashAssoc is performed in a manner similar to
BashArray.  The associative array is first cleared if the assignment operator
is `=`.  Then, the modification of an element is performed for each initializer
item in order.  An item in the initializer list must be in the forms
`[KEY]=VALUE` or `[KEY]=VALUE`.  The element to be modified is specified by
`KEY`.

    declare -A a                # This creates an empty BashAssoc (OSH)
    declare -A a=()             # This creates an empty BashAssoc
    declare -A a=([a]=1 [b]=2)  # This creates a BashAssoc with two elements

    declare -A a=(1 2)          # This is an error (OSH)

    k=10
    declare -A a=([k]=v)        # This creates a BashAssoc with one element,
                                # (['k']=1).  Unlike BashArray, "k" is not
                                # processed by arithmetic expansion.
    a+=([a]=3 [b]=4)            # This adds two elements to the original array.
                                # The result is ([a]=3 [b]=4 [k]=v)
    a+=([k]=5)                  # This overwrites an element in the original
                                # array. The result is ([a]=3 [b]=4 [k]=5).

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
