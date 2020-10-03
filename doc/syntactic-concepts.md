---
in_progress: yes
---

Syntactic Concepts in Oil
=========================

Shell uses sigils like `$`:

    echo $var
    echo "${array[@]}"
    echo "$@"

and sigil pairs:

    echo ${var} 
    echo $(hostname)  
    echo $((1 + 2))

Oil extends these syntactic concepts.

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

## Sigils, Sigil Pairs, and Lexer Modes

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
    ^(echo $PWD) Block Literal      Command        expr         block literals
                                                                look like
                                                                cd / { echo $PWD }
                                                                in command mode

    >(sort -n)   Process Sub        Command        cmd          rare
    <(echo hi)   Process Sub        Command        cmd          rare


    %(array lit) Array Literal      Words          expr

    :(1 + 2)     Lazy Expression    Expression     cmd,expr     
    &(1 + 2)     Eager Expression   Expression     cmd          > &(fd) and > &fd


    $/d+/        Inline Eggex       Eggex          cmd          needs oil-cmd mode

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

    ~() .() -() =() ;() /()    # .() could be easy to confuse with ,()

Oil Process Sub?

    diff <(cat left.txt) <(cat right.txt)
    diff ^(cat left.txt) ^(cat right.txt)  # does this do anything?

Other ideas:

- `%[1 2 3]` for typed arrays.  The entries are dynamically typed check upon
  entry perhaps?
- `%{ }` for table literals / embedded TSV
  - Problem: detecting the last `}` in the word.  Might need to be `~( ... )`
    or something.  Or perhaps `%%( ... )`

Table example:

    var people = %{      # Switches to word mode, but keep track of newlines?
      name      age:Int
      bob       10_000
      'andy c'  15_000
    }
    var people = {name: %(bob 'andy c'), age: %[10_000 15_000]}
