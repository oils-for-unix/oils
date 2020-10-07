A Feel For Oil's Syntax
=======================

Here's one of the shortest ways to describe the [Oil
language]($xref:oil-language):

> A Unix shell that's familiar to people who know Python, JavaScript, or Ruby.

This document gives you a feel for that, with brief examples.  It's not a
comprehensive or precise guide.  Roughly speaking, Oil code has more
punctuation than those 3 languages, but less than shell and Perl.

If you're totally unfamiliar with the language, read [The Simplest Explanation
of Oil ](//www.oilshell.org/blog/2020/01/simplest-explanation.html) first.


<div id="toc">
</div> 

## Preliminaries

Recall that **expression mode** is like Python and appears to the right of `=`:

    var x = 42 + array[i]

And **command mode** is like shell:

    echo $x 

The examples below aren't organized along those lines, but they use `var` and
`echo` to remind you of the context.  Some constructs are valid in both modes.

(I use `echo $x` for familiarity, even though `write -- $x` is more correct.)

## Sigils

Sigils are punctuation characters that precede a name, e.g. the `$` in
`$mystr`.

Unlike Perl and PHP, Oil doesn't use sigils on the LHS of assignments, or in
expression mode.  The [syntactic concepts](syntactic-concepts.html) doc
explains this difference.

### Pervasive

The `$` and `@` sigils mean roughly what they do in shell, Perl, and
PowerShell.

`$` means *string* / *scalar*.  These shell constructs are idiomatic in Oil:

    $mvar   ${myvar}
    $(hostname)

And these Oil language extensions also use `$`:

    echo $[42 + a[i]]            # string interpolation of expression
    echo $len(x)                 # string interpolation of function call
    grep $/ digit+ /             # inline eggex (not implemented yet)

`@` means *array* / *splice an array*:

    echo "$@"                    # Legacy syntax; prefer @ARGV

Oil:

    echo @strs                   # splice array

    echo @split(x) @glob(x)      # splice function that returns array

    for i in @(seq 3) {          # split command sub
      echo $i
    }   

    proc p(first, @rest) {       # named varargs in proc signatures
      write -- $first            # (procs are shell-like functions)
      write -- @rest
    }

### Less Important

Oil doesn't need sigils for hashes, so `%` isn't used the way it's used in
Perl.  Instead, `%` means "unquoted word" in these two cases:

    var mysymbol = %key             # not implemented yet
    var myarray = %(one two three)

These sigils are parsed, but not entirely implemented:

- `&` for Ruby-like blocks in expression mode
- `:` means "out param" / "nameref", or "lazily evaluated"

<!--

`&` means a command block in these 2 cases:

    &(echo $PWD)
    proc foo(x, &myblock) { echo $x; _ evalexpr(myblock) }

`:` means lazily evaluated in these 2 cases (not implemented):

    when :(x > 0) { echo 'positive' }
    x = :[1 + 2]

`:` means "out param" or "nameref" in these 2 cases:

    proc foo(x, :out) {
      setref out = 'z'
    }
    var x
    foo :x   # x is set to z

-->

## Opening and Closing Delimiters

The `{}` `[]` and `()` characters have several different meanings, but we try
our best to make them consistent.  They're subject to legacy constraints from
Bourne shell, Korn shell, and [bash]($xref).

### Braces: Blocks and Dicts

The `{}` characters are used for blocks of code and dict literals (aka hash
tables, associative arrays), which makes Oil look like JavaScript in many
circumstances:

    var d = {name: 'Bob', age: 10}

    while (x > 0) {
      setvar x -= 1
    }

Oil also has Ruby-like blocks:

    cd /tmp {
      echo $PWD
    }

Which can be used for "declarative" configuration:

    server www.example.com {
      port = 80
      root = '/home/www'
      section bar {
        ...
      }
    }

<!--
Future: QTSV / table literals with %{ ... }
-->

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

In [Eggex](eggex.html), they mean grouping and **not** capture, which is
consistent with arithmetic:

    var p = / digit+ ('seconds' | 'minutes' | 'hours' ) /


<!--
    echo .(4 + 5)
    echo foo > &(fd)
-->

### Parens with Sigil: Command Interpolation

The "sigil pairs" with parens enclose commands:

    echo $(ls | wc -l)             # command sub
    echo @(seq 3)                  # split command usb

    var myblock = &(echo $PWD)     # block literal in expression mode

    diff <(sort left.txt) <(sort right.txt)  # bash syntax

And shell words:

    var mylist = %(one two three)  # equivalent to ['one', 'two', 'three']

Unlike brackets and braces, the `()` characters can't appear in shell commands,
which makes them useful as delimiters.

### Brackets: Sequence, Subscript

In expression mode, `[]` means sequence:

    var mylist = ['one', 'two', 'three']

or subscript:

    var item = mylist[1]
    var item = mydict['foo']

### Brackets with a Sigil: Expression

In command mode, it means "expression":

    echo $[1 + 2]

<!--

And are used in type expressions:

    Dict[Int, Str]
    Func[Int => Int]

-->


## Identifier Naming Conventions

`kebab-case` is for procs and filenames:

    gc-test   opt-stats   gen-mypy-asdl

    test/spec-runner.oil   spec/data-enum.tea

`snake_case` is for local variables:

    proc foo {
      var deploy_dest = 'bar@example.com'
      echo $deploy_dest
    }

`CAPS` are used for global variables built into the shell:

    PATH  IFS  UID  HOSTNAME

External programs also accept environment variables in `CAPS`:

    PYTHONPATH  LD_LIBRARY_PATH

(In progress) Global variables that are **silently mutated** by the
interpreter start with `_`:

    _argv   _status   _pipe_status   _line

As do functions to access such mutable vars:

    _match()  _start()   _end()  _field()

<!--

Capital Letters are used for types (Tea Language):

    Bool  Int  Float  Str  List  Dict  Func

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
                              # Consistent with arithmetric expressions!
    < digit+ >                # capturing group
    < digit+ : hour >         # named capture

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

Extended globs are discouraged in Oil because they're a weird way of writing
regular expressions.  But they also use "sigil pairs" with parens:

    ,(*.py|*.sh)   # preferred synonym for @(*.py|*.sh)
    +(...)         # bash/ksh-compatible
    *(...)
    ?(...)
    !(...)

Shell arithmetic is also discouraged in favor of Oil arithmetic:

    echo $((1 + 2))  # shell: confusing coercions, dynamically parsed
    echo $[1 + 2]    # Oil: types, statically parsed

<!--
    ! ?   suffixes (not implemented)
-->

## Related Docs

- [Syntactic Concepts in the Oil Language](syntactic-concepts.html)
- [Language Influences](language-influences.html)
- [Oil Help Topics](oil-help-topics.html).  A comprehensive list of language
  constructs (in progress).

## Appendix: Table of Sigil Pairs

This table is mainly for Oil language designers.  Many constructs aren't
implemented, but we reserve space for them.  The [Oil
Help](oil-help-topics.html) is a better reference for users.

    Example      Description        What's Inside  Lexer Modes  Notes

    $(hostname)  Command Sub        Command        cmd,expr
    @(seq 3)     Split Command Sub  Command        cmd,expr
    &(echo $PWD) Block Literal      Command        expr         block literals
                                                                look like
                                                                cd / { echo $PWD }
                                                                in command mode

    >(sort -n)   Process Sub        Command        cmd          rare
    <(echo hi)   Process Sub        Command        cmd          rare

    %(array lit) Array Literal      Words          expr

    %{table lit} Table Literal      Words, no []   expr         Not implemented yet
                                    or {}


    $[42 + a[i]] Stringify Expr     Expression     cmd
    :[1 + 2]     Lazy Expression    Expression     expr         Not implemented yet

    .(1 + 2)     Typed Expression   Expression     cmd          > .(fd) .(myblock)
                                                                later &fd &myblock
                                                                Not Implemented

    :(a=1, b='') Lazy Arg List      Arg List       cmd,expr     when(), filter()
                                                                mutate()
                                                                Not implemented yet


    $/d+/        Inline Eggex       Eggex          cmd          needs oil-cmd mode
    :/d+/        Lazy Eggex         Eggex          cmd          Not implemented yet

    #'a'         Char Literal       UTF-8 char     expr         Not implemented yet

    c'' c""      C and Raw String   String         expr         add to oil-cmd mode
    r'' r""      Literals

    $''          Shell String       String         cmd          mostly deprecated
                 Literal

    ${x %.3f}    Shell Var Sub      Shell          cmd,expr     mostly deprecated
    $((1+2))     Shell Arith Sub    Shell Arith    cmd          deprecated

    ,(*.py|*.sh) Extended Glob      Glob Words     cmd          deprecated
    +(...)
    *(...)
    ?(...)
    !(...)

Unused sigil pairs:

    ~()   -()   =()   ;()   /()  

<!--

Table example:

    var people = %{      # Switches to word mode, but keep track of newlines?
      name      age:Int
      bob       10_000
      'andy c'  15_000
      [c]
    }
    var people = {name: %(bob 'andy c'), age: %[10_000 15_000]}

But this doesn't work for the same reason!

PARENS

5 Commands:

   2 main command subs with $() and @()
   3 uncommon ones ^() >() <()

1 Words:
   1 with %(array literal)

2 Expressions:
   :(...)  # this is rare, we don't have dplyr

   &(...)  # this is very rare, and honestly the most common case will be
           # echo foo > &myfd, and cd /tmp &myblock
           # So it's really only 1.

BRACKETS

1 Expressions  $[a[i]]

- So honestly () USUALLY means COMMANDS/WORDS
  - I can't flip the whole lanugage from one to another!!!

honestly you could have filter :(a, b) mean an arg list, while

x = :[age > 30]   # This is a lazily evaluated expression.  Ok sure.


- parse_brackets is too pevasive

   # expressions
   $[a[i]]        could also be $a(i)
   $[d->key]      could also be $d('key')

                  @d('key') and @a(i) too?   Confusing
-->


