---
default_highlighter: oils-sh
---

Command vs. Expression Mode
===========================

[YSH][] extends the shell **command** language with a Python-like
**expression** language.

Commands and expressions each have a **lexer mode**, which is an essential
[syntactic concept](syntactic-concepts.html) in YSH.

This doc lists the places where [YSH][] switches between modes.

[YSH]: $xref

<div id="toc">
</div>

## Summary

A main difference is whether you write strings like `unquoted` or `'quoted'`,
and whether you write variables like `$dollar` or `unquoted`:

<style>
thead { text-align: left; }
table {
  width: 100%;
  margin-left: 2em; /* match */
}
</style>

<table>

- thead
  - Description
  - Lexing Mode
  - String
  - Variable
  - Example
- tr
  - Shell-Like
  - Command
  - `unquoted`
  - `$dollar`
  - ```
    ls foo/bar $myvar
    ```
- tr
  - Python-like
  - Expression
  - `'quoted'`
  - `unquoted` 
  - ```
    var s = myfunc('str', myvar)
    ```

</table>

More examples:

    ls foo/bar         # foo and bar are strings - command
    var x = foo / bar  # foo and bar are the names of variables - expression

And:

    echo $filename.py           # $filename is a var - command
    var x = filename ++ '.py'   #  filename is a var - expression

<!--
Shell has a similar difference:

    ls foo/bar        # foo and bar are strings
    a=$(( foo/bar ))  # foo and bar are the names of variables
-->


## From Command Mode to Expression Mode

### RHS of Assignments

Everything after `=` is parsed in expression mode:

    var x = 42 + f(x)    # RHS of var/setvar
    setvar x += g(y)

    setvar x = obj.method()   

This includes *bare assignments* in Hay blocks:

    Rule {
      x = 42 + a[i]
    }

### `=` and `call` keywords

Likewise, everything after `=` or `call` is in expression mode:

    = 42 + f(x)

Throw away the value:

    call mylist->append(x)

### YSH `for while if case`:

Expressions are surrounded by `( )`:

    for k, v in (mydict) { 
      echo "$k $v"
    }

    while (x > 0) {
      setvar x -= 1
    }
    
    if (x > 0) { 
      echo 'positive'
    }

    case (len(x)) {
      (1)    { echo one }
      (2)    { echo two }
      (else) { echo other }
    }

### Expression Sub and Splice

The `$[]` construct converts an expression to a string:

    echo $[42 + a[i]]

The `@[]` construct converts a list to an array of strings:

    echo @[arrayfunc('three', 'four', f(x))]

### Typed Arguments to Procs

Typed arguments are surrounded by `( )`:

    json write (['three', 'four'])
    # =>
    [ "three", "four" ]

Lazy arguments:

    assert [42 === x]

### Proc and Func Parameter Lists

Parameters aren't expressions, but they're parsed with the same lexer:

    proc p (x, y) {    # what's between () is in expression mode
      echo "$x $y"     # back to command mode
    }

    func f(x) {
      return (x)
    }

## From Expression Mode to Command Mode

### Array Literals

    var myarray = :| /tmp/foo ${var} $(echo hi) @myarray |

### Command Sub, Command Literals

Everything in between sigil pairs is in command mode:

    var x = $(hostname | tr a-z A-Z) 

    var y = @(seq 3)   # Split command sub

This is a command literal:

    var b = ^(echo $PWD)

## More Examples

### How Are Glob Patterns Written in Each Mode?

No:

    echo '*.py'              # a literal string, not a glob

    echo @[glob(*.py)]       # syntax error, * is an operator in 
                             # expression mode

    var x = myfunc(*.py)     # ditto, syntax error

Yes:

    echo *.py                # expanded as a glob

    echo @[glob('*.py')]     # A literal string passed to the builtin
                             # glob function

    var x = f('*.py')        # Just a string

    var x = f(glob('*.py'))  # Now it's expanded

Another way to say this is that YSH works like Python:

```python
from glob import glob
glob('*.py')             # this is a glob
os.listdir('*.py')       # no glob because it's not how listdir() works
```

Also note that YSH has a builtin operator that uses glob aka `fnmatch()`
syntax:

    if (x ~~ '*.py') {
      echo 'Python'
    }

