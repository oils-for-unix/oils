---
in_progress: yes
---

Syntactic Concepts in the Oil Language
======================================

Oil borrows popular syntax from many languages, so it has a complex syntax.
Here are some concepts that may help you learn and remember it.


- Static Parsing: For better errors, and for tooling.
- Parse Options: for compatibility.
- Command vs. Expression Mode.  The expression mode is the major
  new part of Oil.
- Lexer Modes: There are actually more than two.  Oil uses two, but bash uses many.
- Sigils and Sigil Pairs.

<div id="toc">
</div> 


## Static Parsing

Like Python, JS.  See Oil language definition.

- `[[ ]]` vs `[]`
- `echo -e` vs `$''`
- shell arithmetic vs. Oil arithmetic, e.g. `0xff`
- assignment builtins vs. Oil assignment (`var`, `setvar`, etc.)

Remaining dynamic parsing in shell:

- printf: `%.3f`
- glob: `*.py'`
- history lexer does another pass ...

## Parsing Options to Take Over @, (), {}, `set`, and maybe =

Another concept is parsing modes.

    shopt -s all:oil  # most important thing, turns on many options

    if ( ) {
    }

    echo @array

    set x = 1
    builtin set -o errexit

equals:

    x = 1
    equivalent to 
    const x = 1

This is for Oil as a **configuration language**.

## Command vs. Expression Mode

See [Command vs. Expression Mode](command-vs-expression-mode.html).

    echo hi

Expression mode in three places:

    echo @array
    myprog --flag=$f(x, y)
    var z = f(x+1, y)

Control Flow:

    if grep foo
    if (foo) {}   # replaces if [ -n $foo ]; then

    while

    for

    switch/case -- for translation to C++ like mycpp
    match/case

## Lexer Modes

More


## Sigils, Sigil Pairs

Shell uses sigils like `$`:

    echo $var
    echo "${array[@]}"
    echo "$@"

and sigil pairs:

    echo ${var} 
    echo $(hostname)  
    echo $((1 + 2))

Oil extends them.


A sigil is a symbol that prefixes a "name":

- `$foo` for string
- `@array` for array of strings
- `:` sort of means unevaluated
  - `:interned` could be an unevaluated but interned string/variable name
  - `:(1 + 2)`
  - unfortunately `^(echo hi)` is not symmetrical, but there's a reason for
    that

A sigil pair encloses other symbols, as in `$(echo hi)` or `r'raw string'`.  The
opening/left bracket is generally 2 characters, and the closing/right bracket
is generally 1.

Each sigil pair may be available in:

- the command lexer mode,
- the Oil expression lexer mode,  
- or both

And it may change the lexer mode, based on what's inside.

## Appendix: Table of Sigil Pairs


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

    %{table lit} Table Literal      Words, no []   expr         Not implemented
                                    or {}


    $[1 + a[i]]  Stringify Expr     Expression     cmd
    :[1 + 2]     Lazy Expression    Expression     expr         Not implemented

    .(1 + 2)     Typed Expression   Expression     cmd          > .(fd) .(myblock)
                                                                later &fd &myblock
                                                                Not Implemented

    :(a=1, b='') Lazy Arg List      Arg List       cmd,expr     when(), filter()
                                                                mutate()
                                                                Not Implemented


    $/d+/        Inline Eggex       Eggex          cmd          needs oil-cmd mode

    #'a'         Char Literal       UTF-8 char     expr         Not implemented

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

## Related Documents

- [Ideas for Future Deprecations](future.html).  We can reduce the overloading
  of parens by taking back `[]` as operator characters, and globbing with
  `@'*.[ch]'`.

