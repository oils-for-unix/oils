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

## Rough Idea

`$` means "string":

    $var   ${var}   $(hostname)   $[hostname]   $len(x)
    $/ digit+ /

`@` means array:

    write -- @strs
    for i in @(seq 3) { echo $i }
    @[seq 3]  # new style
    @split(x)  @glob(x)
    proc(first, @rest) {  write -- @rest }

`[]` means sequence:

    ['one', 'two', 'three']
    %[one two three]
    $[echo hi]  # new style
    @[seq 3]    # new style

And are used in type expressions:

    Dict[Int, Str]
    Func[Int => Int]

`()` means runtime expressions / typed data:

    setvar x = (1 + 2) * 3

    if (x > 0) {
      echo 'positive'
    }

    echo .(4 + 5)
    echo foo > &(fd)

`{}` means dict / block / name-value:

    d = {name: 'Bob'}

    while (x > 0) {
      setvar x -= 1
    }

    server foo {
      name = 'Bob'
    }

Kebab-case is for procs and filenames:

    gc-test   opt-stats   gen-mypy-asdl

    test/spec-runner.oil   spec/data-enum.tea

Capital Letters are used for types:

    Bool  Int  Float  Str  List  Dict  Func

    class Parser { }
    data Point(x Int, y Int)

    enum Expr { Unary(child Expr), Binary(left Expr, right Expr) }

ALL CAPS are used for global variables:

    PATH  IFS  UID  HOSTNAME

And external programs accept environment variables in all caps:

    PYTHONPATH  LD_LIBRARY_PATH

Global variables that are silently mutated by the interpreter:

    _argv  _status   _pipe_status

And functions to access such mutable vars:

    _match  _start   _end   _field

Less important sigils:

`:` means unevaluated:

    :myname
    :(1 + 2)

`^` means a command block:

    ^(echo $PWD)
    ^[echo $PWD]  # new style
    proc foo(x, ^block) { echo $x; _ run(block) }


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
    &(echo $PWD) Block Literal      Command        expr         block literals
                                                                look like
                                                                cd / { echo $PWD }
                                                                in command mode

    >(sort -n)   Process Sub        Command        cmd          rare
    <(echo hi)   Process Sub        Command        cmd          rare

    %(array lit) Array Literal      Words          expr


    $[1 + a[i]]  Stringify Expr     Expression     cmd
    :[1 + 2]     Lazy Expression    Expression     expr

    .(1 + 2)     Typed Expression   Expression     cmd          > .(fd) .(myblock)
    :(a=1, b='') Lazy Arg List      Arg List       cmd,expr     filter(), mutate()


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

Notes:

- Don't really need `&(fd)`?  Could use `.(myfd)` and `.(myblock)`

Unused sigil pairs:

    ~() .() -() =() ;() /()    # .() could be easy to confuse with ,()

Other ideas:

- `%[1 2 3]` for typed arrays.  The entries are dynamically typed check upon
  entry perhaps?

<!--

Table example:

    var people = %{      # Switches to word mode, but keep track of newlines?
      name      age:Int
      bob       10_000
      'andy c'  15_000
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

