---
default_highlighter: oils-sh
---

A Feel For YSH Syntax
=====================

A short way to describe the [YSH]($xref) language:

> A Unix shell that's familiar to people who know Python, JavaScript, or Ruby.

This document gives you a feel for that, with brief examples.  It's not a
comprehensive or precise guide.  Roughly speaking, YSH code has more
punctuation than those 3 languages, but less than shell and Perl.

If you're totally unfamiliar with the language, read [The Simplest Explanation
of Oil](//www.oilshell.org/blog/2020/01/simplest-explanation.html) first.  (Oil
was renamed [YSH]($xref) in 2023.)

<div id="toc">
</div> 

## Preliminaries

Different parts of YSH are parsed in either **command** or **expression** mode.
Command mode is like shell:

    echo $x 

Expression mode looks like Python or JavaScript, and appears on right-hand side
of `=`:

    var x = 42 + array[i]

The examples below aren't organized along those lines, but they use `var` and
`echo` to remind you of the context.  Some constructs are valid in both modes.

## Sigils

Sigils are punctuation characters that precede a name, e.g. the `$` in
`$mystr`.

Unlike Perl and PHP, YSH doesn't use sigils on the LHS of assignments, or in
expression mode.  The [syntactic concepts](syntactic-concepts.html) doc
explains this difference.

### Very Common

The `$` and `@` sigils mean roughly what they do in shell, Perl, and
PowerShell.

`$` means *string* / *scalar*.  These shell constructs are idiomatic in YSH:

    $mvar   ${myvar}
    $(hostname)

And these YSH language extensions also use `$`:

    echo $[42 + a[i]]            # string interpolation of expression
    grep $/ digit+ /             # inline eggex (not implemented yet)

`@` means *array* / *splice an array*:

    echo "$@"                    # Legacy syntax; prefer @ARGV

YSH:

    echo @strs                   # splice array

    echo @[split(x)] @[glob(x)]  # splice expressions that returns arrays

    for i in @(seq 3) {          # split command sub
      echo $i
    }   

    proc p(first, @rest) {       # named varargs in proc signatures
      write -- $first            # (procs are shell-like functions)
      write -- @rest
    }

### Less Common

The colon means "unquoted word" in these two lines:

    var mysymbol = :key               # string, not implemented yet
    var myarray = :| one two three |  # array

It's also used to pass the name of a variable to a builtin:

    echo hi | read :myvar

A caret means "unevaluated":

    var cmd = ^(cd /tmp; ls *.txt)
    var expr = ^[42 + a[i]]  # unimplemented
    var template = ^"var = $var"  # unimplemented

<!--

`:` means lazily evaluated in these 2 cases (not implemented):

    when :(x > 0) { echo 'positive' }
    x = :[1 + 2]

-->

## Opening and Closing Delimiters

The `{}` `[]` and `()` characters have several different meanings, but we try
our best to make them consistent.  They're subject to legacy constraints from
Bourne shell, Korn shell, and [bash]($xref).

### Braces: Command Blocks and Dict Literal Expressions

In expression mode, `{}` are used for dict literals (aka hash
tables, associative arrays), which makes YSH look like JavaScript:


    var d = {name: 'Bob', age: 10}

    while (x > 0) {
      setvar x -= 1
    }

In command mode, they're used for blocks of code:

    cd /tmp {
      echo $PWD
    }

Blocks are also used for "declarative" configuration:

    server www.example.com {
      port = 80
      root = '/home/www'
      section bar {
        ...
      }
    }

### Parens: Expression

Parens are used in expressions:

    var x = (42 + a[i]) * myfunc(42, 'foo')

    if (x > 0) {         # compare with if test -d /tmp
      echo 'positive'
    }

And signatures:

    proc p(x, y) {
      echo $x $y
    }

In [Eggex](eggex.html), they mean **grouping** and not capture, which is
consistent with other YSH expressions:

    var p = / digit+ ('seconds' | 'minutes' | 'hours' ) /


<!--
    echo .(4 + 5)
    echo foo > &(fd)
-->

### Parens with Sigil: Command Interpolation

The "sigil pairs" with parens enclose commands:

    echo $(ls | wc -l)             # command sub
    echo @(seq 3)                  # split command sub

    var myblock = ^(echo $PWD)     # block literal in expression mode

    diff <(sort left.txt) <(sort right.txt)  # bash syntax

Unlike brackets and braces, the `()` characters can't appear in shell commands,
which makes them useful as delimiters.

### Brackets: Sequence, Subscript

In expression mode, `[]` means sequence:

    var mylist = ['one', 'two', 'three']

or subscript:

    var item = mylist[1]
    var item = mydict['foo']

### Brackets with a Sigil: Expression

The sigil pair `$[]` is common in command mode:

    echo $[42 + a[i]]

Quotations are valid in expression mode:

    var my_expr = ^[42 + a[i]]

Pass lazy arg lists to commands with `[]`.  They're syntactic sugar for `^[]`:

    assert [42 === x]     # short version

    assert (^[42 === x])  # same thing

<!--

And are used in type expressions:

    Dict[Int, Str]
    Func[Int => Int]

-->

## Spaces Around `=` ?

In YSH, *your own* variables look like this:

    const x = 42
    var s = 'foo'
    setvar s = 'bar'

In contrast, special shell variables are written with a single `NAME=value`
argument:

    shvar PATH=/tmp {
      temporary
    }

Which is similar to the syntax of the `env` command:

    env PYTHONPATH=/tmp ./myscript.py


## Naming Conventions for Identifiers

See the [Style Guide](style-guide.html).

<!--

    class Parser { }
    data Point(x Int, y Int)

    enum Expr { Unary(child Expr), Binary(left Expr, right Expr) }
-->

## Other Punctuation Usage

Here are other usages of the punctuation discussed:

    echo *.[ch]                    # glob char and char classes
    echo {alice,bob}@example.com   # brace expansion

Eggex:

    / [a-f A-F 0-9] /         # char classes use []

    / digit+ ('ms' | 'us') /  # non-capturing group
    < digit+ >                # capturing group
    < digit+ :hour >          # named capture

    dot{3,4} a{+ N}           # repetition

The `~` character is used in operators that mean "pattern" or "approximate":

    if (s ~ /d+/) {
      echo 'number'
    }   

    if (s ~~ '*.py') {
      echo 'Python'
    }

    if (mystr ~== myint) {
      echo 'string equals number'
    }

Extended globs are discouraged in YSH because they're a weird way of writing
regular expressions.  But they also use "sigil pairs" with parens:

    ,(*.py|*.sh)   # preferred synonym for @(*.py|*.sh)
    +(...)         # bash/ksh-compatible
    *(...)
    ?(...)
    !(...)

Shell arithmetic is also discouraged in favor of YSH arithmetic:

    echo $((1 + 2))  # shell: confusing coercions, dynamically parsed
    echo $[1 + 2]    # YSH: types, statically parsed

<!--
    ! ?   suffixes (not implemented)
-->

## Related Docs

- [Syntactic Concepts in the YSH Language](syntactic-concepts.html)
- [Language Influences](language-influences.html)

## Appendix: Table of Sigil Pairs

This table is mainly for YSH language designers.  Some constructs aren't
implemented, but we reserve space for them.  The [Oils
Reference](ref/index.html) is more complete.

    Example      Description        What's Inside  Where Valid  Notes

    $(hostname)  Command Sub        Command        cmd,expr
    @(seq 3)     Split Command Sub  Command        cmd,expr     should decode J8
                                                                strings

    { echo hi }  Block Literal      Command        cmd          shell requires ;
    ^(echo hi)   Unevaluated Block  Command        expr         rare

    >(sort -n)   Process Sub        Command        cmd          rare
    <(echo hi)   Process Sub        Command        cmd          rare

    :|foo $bar|  Array Literal      Words          expr

    $[42 + a[i]] Stringify Expr     Expression     cmd,expr
    @[glob(x)]   Array-ify Expr     Expression     cmd,expr
    ^[42 + a[i]] Unevaluated Expr   Expression     expr

    ^"$1 $2"     value.Expr         DQ String      expr 

    ${x %2d}     Var Sub            Formatting     cmd,expr     not implemented
    ${x|html}    Var Sub            Formatting     cmd,expr     not implemented

    pp (x)       Typed Arg List     Argument       cmd
                                    Expressions

    pp [x]       Lazy Arrg list     Argument       cmd
                                    Expressions

    $/d+/        Inline Eggex       Eggex Expr     cmd          not implemented

    $"x is $x"   Interpolated       DQ string      cmd,expr     usually "x is $x"
                 string                                         $ is optional

    r'foo\bar'   Raw String         String         expr         cmd when shopt
                 Literal                                        parse_raw_string

    u''   b''    J8 Literals        String         cmd,expr,data

    j""          JSON8 String       String         data
                 Literal

Discouraged / Deprecated

    ${x%%pre}    Shell Var Sub      Shell          cmd,expr     mostly deprecated
    $((1+2))     Shell Arith Sub    Shell Arith    cmd          deprecated

    @(*.py|*.sh) Extended Glob      Glob Words     cmd          deprecated
    +(...)
    *(...)
    ?(...)
    !(...)

    ,(*.py|*.sh) Extended Glob      Glob Words     cmd          break conflict
                                                                with split command
                                                                sub

Key to "where valid" column:

- `cmd` means `lex_mode_e.ShCommand`
- `expr` means `lex_mode_e.Expr`
- `data` means it's valid in J8 Notation

Some unused sigil pairs:

    ~()   -()   =()   /()   _()   .()

