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

## Literals

### bool-literal

YSH uses JavaScript-like spellings for these three "atoms":

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

YSH strings appear in expression contexts, and look like shell strings:

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

YSH has four pattern matching operators: `~   !~   ~~   !~~`.

Does string match an **eggex**?

    var filename = 'x42.py'
    if (filename ~ / d+ /) {
      echo 'number'
    }

Does a string match a POSIX regular expression (ERE syntax)?

    if (filename ~ '[[:digit:]]+') {
      echo 'number'
    }

Negate the result with the `!~` operator:

    if (filename !~ /space/ ) {
      echo 'no space'
    }

    if (filename !~ '[[:space:]]' ) {
      echo 'no space'
    }

Does a string match a **glob**?

    if (filename ~~ '*.py') {
      echo 'Python'
    }

    if (filename !~~ '*.py') {
      echo 'not Python'
    }

Take care not to confuse glob patterns and regular expressions.

- Related doc: [YSH Regex API](../ysh-regex-api.html)

## Eggex

### re-literal

Examples of eggex literals:

    var pat = / d+ /  # => [[:digit:]]+

You can specify flags passed to libc regcomp():

    var pat = / d+ ; reg_icase reg_newline / 

You can specify a translation preference after a second semi-colon:

    var pat = / d+ ; ; ERE / 

Right now the translation preference does nothing.  It could be used to
translate eggex to PCRE or Python syntax.

- Related doc: [Egg Expressions](../eggex.html)

### re-primitive

    %zero    'sq'
    Subpattern   @subpattern

### class-literal

    [c a-z 'abc' @str_var \\ \xFF \u0100]

Negated:

    ![a-z]

### named-class

    dot
    digit  space  word
    d  s  w

Negated:

    !digit   !space   !word

### re-compound

    pat|alt   pat seq   (group)

### re-capture

    <capture d+ as name: int>

### re-flags

Valid ERE flags, which are passed to libc's `regcomp()`:

- `reg_icase` aka `i` (ignore case)
- `reg_newline` (4 changes regarding newlines)

See `man regcomp`.

### re-multiline

Not implemented.  Splicing makes it less necessary:

    var Name  = / <capture [a-z]+ as name> /
    var Num   = / <capture d+ as num> /
    var Space = / <capture s+ as space> /

    # For variables named like CapWords, splicing @Name doesn't require @
    var lexer = / Name | Num | Space /
