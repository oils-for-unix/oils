---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

YSH Expression Language
===

This chapter in the [Oils Reference](index.html) describes the YSH expression
language, which includes [Egg Expressions]($xref:eggex).

<div id="toc">
</div>

## Keywords

### const 

Binds a name to a YSH expression on the right, with a **dynamic** check to
prevent mutation.

    const c = 'mystr'        # equivalent to readonly c=mystr
    const pat = / digit+ /   # an eggex, with no shell equivalent

If you try to re-declare or mutate the name, the shell will fail with a runtime
error.  `const` uses the same mechanism as the `readonly` builtin.

Consts should only appear at the top-level, and can't appear within `proc` or
`func`.

### var

Initializes a name to a YSH expression.

    var s = 'mystr'        # equivalent to declare s=mystr
    var pat = / digit+ /   # an eggex, with no shell equivalent

It's either global or scoped to the current function.

You can bind multiple variables:

    var flag, i = parseArgs(spec, ARGV)

    var x, y = 42, 43

You can omit the right-hand side:

    var x, y  # implicitly initialized to null

### setvar

At the top-level, setvar creates or mutates a variable.

    setvar gFoo = 'mutable'

Inside a func or proc, it mutates a local variable declared with var.

    proc p {
      var x = 42
      setvar x = 43
    }

You can mutate a List location:

    setvar a[42] = 'foo'

Or a Dict location:

    setvar d['key'] = 43
    setvar d.key = 43  # same thing

You can use any of these these augmented assignment operators

    +=   -=   *=   /=   **=   //=   %=
    &=   |=   ^=   <<=   >>=

Examples:

    setvar x += 2  # increment by 2

    setvar a[42] *= 2  # multiply by 2

    setvar d.flags |= 0b0010_000  # set a flag


### setglobal

Creates or mutates a global variable.  Has the same syntax as `setvar`.

## Literals

### bool-literal

Oil uses JavaScript-like spellings for these three "atoms":

    true   false   null

Note that the empty string is a good "special" value in some cases.  The `null`
value can't be interpolated into words.

### int-literal

    var myint = 42
    var myfloat = 3.14
    var float2 = 1e100

### rune-literal

    #'a'   #'_'   \n   \\   \u{3bc}

### str-literal

Oil strings appear in expression contexts, and look like shell strings:

    var s = 'foo'
    var double = "hello $world and $(hostname)"

However, strings with backslashes are forced to specify whether they're **raw**
strings or C-style strings:

    var s = 'line\n'    # parse error: ambiguous

    var s = $'line\n'   # C-style string

    var s = r'[a-z]\n'  # raw strings are useful for regexes (not eggexes)

    var unicode = 'mu = \u{3bc}'

### list-literal

Lists have a Python-like syntax:

    var mylist = ['one', 'two', 3]

And a shell-like syntax:

    var list2 = %| one two |

The shell-like syntax accepts the same syntax that a command can:

    ls $mystr @ARGV *.py {foo,bar}@example.com

    # Rather than executing ls, evaluate and store words
    var cmd = :| ls $mystr @ARGV *.py {foo,bar}@example.com |

### dict-literal

    {name: 'value'}

### range

A range is a sequence of numbers that can be iterated over:

    for i in (0 .. 3) {
      echo $i
    }
    => 0
    => 1
    => 2

As with slices, the last number isn't included.  Idiom to iterate from 1 to n:

    for i in (1 .. n+1) {
      echo $i
    }

### block-literal

    var myblock = ^(echo $PWD)

### expr-lit

    var myexpr = ^[1 + 2*3]

## Operators

### concat

    var s = 's'
    var concat1 = s ++ '_suffix'
    var concat2 = "${s}_suffix"  # similar

    var c = :| one two |
    var concat3 = c ++ :| three 4 |
    var concat4 = :| @c three 4 |

    var mydict = {a: 1, b: 2}
    var otherdict = {a: 10, c: 20}
    var concat5 = mydict ++ otherdict


### ysh-compare

    a == b        # Python-like equality, no type conversion
    3 ~== 3.0     # True, type conversion
    3 ~== '3'     # True, type conversion
    3 ~== '3.0'   # True, type conversion

### ysh-logical

    not  and  or

Note that these are distinct from `!  &&  ||`.

### ysh-arith

    +  -  *  /   //   %   **

### ysh-bitwise

    ~  &  |  ^

### ysh-ternary

Like Python:

    display = 'yes' if len(s) else 'empty'

### ysh-index

Like Python:

    myarray[3]
    mystr[3]

TODO: Does string indexing give you an integer back?

### ysh-slice

Like Python:

    myarray[1 : -1]
    mystr[1 : -1]

### func-call

Like Python:

    f(x, y)

### thin-arrow

The thin arrow is for mutating methods:

    var mylist = ['bar']
    call mylist->pop()

<!--
TODO
    var mydict = {name: 'foo'}
    call mydict->erase('name')
-->

### fat-arrow

The fat arrow is for transforming methods:

    if (s => startsWith('prefix')) {
      echo 'yes'
    }

If the method lookup on `s` fails, it looks for free functions.  This means it
can be used for "chaining" transformations:

    var x = myFunc() => list() => join()

### match-ops

    ~   !~   ~~   !~~

## Eggex

### re-literal

### re-compound

### re-primitive

### named-class

### class-literal

### re-flags

### re-multiline

Not implemented.


