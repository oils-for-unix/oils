---
in_progress: yes
body_css_class: width40 help-body
default_highlighter: oil-sh
---

YSH Expression Language
===

This chapter in the [Oils Reference](index.html) describes the YSH expression
language, which includes [Egg Expressions]($xref:eggex).

<div id="toc">
</div>

## Keywords

### const 

Initializes a constant name to the Oil expression on the right.

    const c = 'mystr'        # equivalent to readonly c=mystr
    const pat = / digit+ /   # an eggex, with no shell equivalent

It's either a global constant or scoped to the current function.

### var

Initializes a name to the Oil expression on the right.

    var s = 'mystr'        # equivalent to declare s=mystr
    var pat = / digit+ /   # an eggex, with no shell equivalent

It's either global or scoped to the current function.

### setvar

At the top-level, setvar creates or mutates a variable.

Inside a proc, it mutates a local variable declared with var.

### setglobal

Creates or mutates a global variable.

### setref

Mutates a variable through a named reference.  See examples in
doc/variables.md.


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

### arrow-method

Transforming methods use the `->` operator:

    var b = s->startswith('prefix')

### mut-method

Mutating methods use the `:` operator

    var mydict = {name: 'foo'}
    :: mydict.erase('name')

    var mylist = ['bar']
    :: mylist.pop()

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


