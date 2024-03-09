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

### ysh-string

Double quoted strings are identical to shell:

    var dq = "hello $world and $(hostname)"

Single quoted strings may be raw:

    var s = r'line\n'      # raw string means \n is literal, NOT a newline

Or escaped *J8 strings*:

    var s = u'line\n \u{3bc}'        # unicode string means \n is a newline
    var s = b'line\n \u{3bc} \yff'   # same thing, but also allows bytes

Both `u''` and `b''` strings evaluate to the single `Str` type.  The difference
is that `b''` strings allow the `\yff` byte escape.

---

There's no way to express a single quote in raw strings.  Use one of the other
forms instead:

    var sq = "single quote: ' "
    var sq = u'single quote: \' '

Sometimes you can omit the `r`, e.g. where there are no backslashes and thus no
ambiguity:

    echo 'foo'
    echo r'foo'  # same thing

The `u''` and `b''` strings are called *J8 strings* because the syntax in YSH
**code** matches JSON-like **data**.

    var strU = u'mu = \u{3bc}'  # J8 string with escapes
    var strB = b'bytes \yff'    # J8 string that can express byte strings

More examples:

    var myRaw = r'[a-z]\n'      # raw strings are useful for regexes (not
                                # eggexes)

### triple-quoted

Triple-quoted string literals have leading whitespace stripped on each line.
They come in the same variants:

    var dq = """
        hello $world and $(hostname)
        no leading whitespace
        """

    var myRaw = r'''
        raw string
        no leading whitespace
        '''

    var strU = u'''
        string that happens to be unicode \u{3bc}
        no leading whitespace
        '''

    var strB = b'''
        string that happens to be bytes \u{3bc} \yff
        no leading whitespace
        '''

Again, you can omit the `r` prefix if there's no backslash, because it's not
ambiguous:

    var myRaw = '''
        raw string
        no leading whitespace
        '''

### str-template

String templates use the same syntax as double-quoted strings:

    var mytemplate = ^"name = $name, age = $age"

Related topics:

- [Str => replace](chap-type-method.html#replace)
- [ysh-string](chap-expr-lang.html#ysh-string)

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

<h3 id="concat">concat <code>++</code></h3>

The concatenation operator works on strings:

    var s = 'hello'
    var t = s ++ ' world'
    = t
    (Str)   "hello world"

and lists:

    var L = ['one', 'two']
    var M = L ++ ['three', '4']
    = M
    (List)   ["one", "two", "three", "4"]

String interpolation can be nicer than `++`:

    var t2 = "${s} world"  # same as t

Likewise, splicing lists can be nicer:

    var M2 = :| @L three 4 |  # same as M

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

An eggex literal looks like this:

    / expression ; flags ; translation preference /

The flags and translation preference are both optional.

Examples:

    var pat = / d+ /  # => [[:digit:]]+

You can specify flags passed to libc `regcomp()`:

    var pat = / d+ ; reg_icase reg_newline / 

You can specify a translation preference after a second semi-colon:

    var pat = / d+ ; ; ERE / 

Right now the translation preference does nothing.  It could be used to
translate eggex to PCRE or Python syntax.

- Related doc: [Egg Expressions](../eggex.html)

### re-primitive

There are two kinds of eggex primitives.

"Zero-width assertions" match a position rather than a character:

    %start           # translates to ^
    %end             # translates to $

Literal characters appear within **single** quotes:

    'oh *really*'    # translates to regex-escaped string

Double-quoted strings are **not** eggex primitives.  Instead, you can use
splicing of strings:

    var dq = "hi $name"    
    var eggex = / @dq /

### class-literal

An eggex character class literal specifies a set.  It can have individual
characters and ranges:

    [ 'x' 'y' 'z' a-f A-F 0-9 ]  # 3 chars, 3 ranges

Omit quotes on ASCII characters:

    [ x y z ]  # avoid typing 'x' 'y' 'z'

Sets of characters can be written as trings

    [ 'xyz' ]  # any of 3 chars, not a sequence of 3 chars

Backslash escapes are respected:

    [ \\ \' \" \0 ]
    [ \xFF \u0100 ]

Splicing:

    [ @str_var ]

Negation always uses `!`

    ![ a-f A-F 'xyz' @str_var ]

### named-class

Perl-like shortcuts for sets of characters:

    [ dot ]    # => .
    [ digit ]  # => [[:digit:]]
    [ space ]  # => [[:space:]]
    [ word ]   # => [[:alpha:]][[:digit:]]_

Abbreviations:

    [ d s w ]  # Same as [ digit space word ]

Valid POSIX classes:

    alnum   cntrl   lower   space
    alpha   digit   print   upper
    blank   graph   punct   xdigit

Negated:

    !digit   !space   !word
    !d   !s   !w
    !alnum  # etc.

### re-repeat

Eggex repetition looks like POSIX syntax:

    / 'a'? /      # zero or one
    / 'a'* /      # zero or more
    / 'a'+ /      # one or more

Counted repetitions:

    / 'a'{3} /    # exactly 3 repetitions
    / 'a'{2,4} /  # between 2 to 4 repetitions

### re-compound

Sequence expressions with a space:

    / word digit digit /   # Matches 3 characters in sequence
                           # Examples: a42, b51

(Compare `/ [ word digit ] /`, which is a set matching 1 character.)

Alternation with `|`:

    / word | digit /       # Matches 'a' OR '9', for example

Grouping with parentheses:

    / (word digit) | \\ /  # Matches a9 or \

### re-capture

To retrieve a substring of a string that matches an Eggex, use a "capture
group" like `<capture ...>`.

Here's an eggex with a **positional** capture:

    var pat = / 'hi ' <capture d+> /  # access with _group(1)
                                      # or Match => _group(1)

Captures can be **named**:

    <capture d+ as month>       # access with _group('month')
                                # or Match => group('month')

Captures can also have a type **conversion func**:

    <capture d+ : int>          # _group(1) returns Int

    <capture d+ as month: int>  # _group('month') returns Int

Related docs and help topics:

- [YSH Regex API](../ysh-regex-api.html)
- [`_group()`](chap-builtin-func.html#_group)
- [`Match => group()`](chap-type-method.html#group)

### re-splice

To build an eggex out of smaller expressions, you can **splice** eggexes
together:

    var D = / [0-9][0-9] /
    var time = / @D ':' @D /  # [0-9][0-9]:[0-9][0-9]

If the variable begins with a capital letter, you can omit `@`:

    var ip = / D ':' D /

You can also splice a string:

    var greeting = 'hi'
    var pat = / @greeting ' world' /  # hi world

Splicing is **not** string concatenation; it works on eggex subtrees.

### re-flags

Valid ERE flags, which are passed to libc's `regcomp()`:

- `reg_icase` aka `i` - ignore case
- `reg_newline` - 4 matching changes related to newlines

See `man regcomp`.

### re-multiline

Multi-line eggexes aren't yet implemented.  Splicing makes it less necessary:

    var Name  = / <capture [a-z]+ as name> /
    var Num   = / <capture d+ as num> /
    var Space = / <capture s+ as space> /

    # For variables named like CapWords, splicing @Name doesn't require @
    var lexer = / Name | Num | Space /
