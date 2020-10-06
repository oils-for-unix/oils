---
in_progress: yes
---

Feelings About Oil Syntax (A Rough Guide)
=========================================

These rough feeligsn may help you learn and remember Oil's syntax.

It helped me design the syntax.

This is not a comprehensive guide.

TODO:

    *.[ch]  # glob cahracter
    {a,b}@example.com

    []                    # eggex char class
    ()                    # eggex non-capturing groups.  Now consistent!!!
    <>                    # eggex named capture
    dot{3,4}  and a{+ N} # repetition


Approximate or pattern:

    ~     regex
    ~~    glob/fnmatch
    ~==   type converting equality

    ! ?   suffixes (not implemented)

<div id="toc">
</div> 

## Sigils

The `$` and `@` characters are mean roughly the same thing as they do in shell,
Perl, PowerShell, etc.

`$` means "string":

    $var   ${var}   $(hostname)     # shell constructs
    $[42 + a[i]]                    # string interpolation of expression
    $len(x)                         # string interpolation of function call
    $/ digit+ /                     # inline eggex, not implemented

`@` means array:

    write -- @strs                  # splice
    write -- @split(x) @glob(x)     # function call that returns array

    for i in @(seq 3) {             # split command sub
      echo $i
    }   

    proc(first, @rest) {            # proc signature
      write -- @rest
    }

### Less Important Sigils (mostly unimplemented)

`&` means a command block in these 2 cases:

    &(echo $PWD)
    proc foo(x, &myblock) { echo $x; _ evalexpr(myblock) }

`%` means "unquoted word" in these two cases:

    mysymbol = %key             # not implemented
    myarray = %(one two three)

`:` means lazily evaluated in these 2 cases (not implemented):

    when :(x > 0) { echo 'positive' }
    x = :[1 + 2]

`:` means "out param" or "nameref" in these 2 cases:

    proc foo(x, :out) {
      setref out = 'z'
    }
    var x
    foo :x   # x is set to z

## Braces / Parens / Brackets

`{}` means dict / block / name-value:

    d = {name: 'Bob'}

    while (x > 0) {
      setvar x -= 1
    }

    server foo {
      name = 'Bob'
    }

<!--
Future: QTSV / table literals with %{ ... }
-->


### `[]` and `()` are the most inconsistent

Unfortunately the meaning of `[]` and `()` is not consistent due to
compatibility with shell.

`[]` means sequence:

    ['one', 'two', 'three']

And sometimes expressions:

    $[1 + 2]

And are used in type expressions:

    Dict[Int, Str]
    Func[Int => Int]

`()` is the most overloaded one.

It means expressions:

    setvar x = (1 + 2) * 3

    if (x > 0) {
      echo 'positive'
    }

    echo .(4 + 5)
    echo foo > &(fd)

And also commands/words: note that `()` are shell operator characters)

    $(echo hi | wc -l)  # command sub
    @(seq 3)            # split command usb
    &(echo $PWD)        # block literal

Related, it means words too:

    %(one two three)

## Lowercase or Capital Letters?

`kebab-case` is for procs and filenames:

    gc-test   opt-stats   gen-mypy-asdl

    test/spec-runner.oil   spec/data-enum.tea

`snake_case` for local variables:

    proc foo {
      var deploy_dest = 'foo@example.com'
      echo $deploy_dest
    }

ALL CAPS are used for global variables:

    PATH  IFS  UID  HOSTNAME

And external programs accept environment variables in all caps:

    PYTHONPATH  LD_LIBRARY_PATH

Global variables that are silently mutated by the interpreter:

    _argv  _status   _pipe_status

And functions to access such mutable vars:

    _match  _start   _end   _field

Capital Letters are used for types (Tea Language):

    Bool  Int  Float  Str  List  Dict  Func

    class Parser { }
    data Point(x Int, y Int)

    enum Expr { Unary(child Expr), Binary(left Expr, right Expr) }

## Related Docs

- [Syntactic Concepts in the Oil Language](syntactic-concepts.html)

