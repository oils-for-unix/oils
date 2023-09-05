---
default_highlighter: oil-sh
---

Command vs. Expression Mode
===========================

This is an essential [syntactic concept](syntactic-concepts.html) in YSH.

YSH extends the shell **command** language with a Python-like **expression**
language.

To implement that, the lexer enters "expression mode".

The key difference is that when lexing commands, `unquoted` is a string, while
`$dollar` is a variable:

    ls /bin/str $myvar

On the other hand, when lexing expressions, `'quoted'` is a string, while
`unquoted` is a variable:

    var s = myfunc('str', myvar)

This doc lists the places where we switch modes.

<div id="toc">
</div>

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

### `=` and `_` keywords

Likewise, everything after `=` or `_` is in expression mode:

    = 42 + f(x)

Throw away the value:

    _ L.append(x)

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

### Proc and Func Parameter Lists

Parameters aren't expressions, but they're parsed with the same lexer:

    proc p(x, y) {    # what's between () is in expression mode
      echo "$x $y"    # back to command mode
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

## Examples

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


## vim: sw=2
