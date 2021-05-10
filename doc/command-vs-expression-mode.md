---
default_highlighter: oil-sh
---

Command vs. Expression Mode
===========================

This is an essential [syntactic concept](syntactic-concepts.html) in Oil.

Oil is an extension of the shell language, which consists of **commands**.  The
most important addition is a Python-like **expression language**.  To implement
that, the lexer enters "expression mode".

Here's the key difference:

 In command mode, `unquoted` is a string, while `$dollar` is a variable:

    ls /bin/str $myvar

In expression mode: `'quoted'` is a string, while `unquoted` is a variable:

    var s = myfunc('str', myvar)


<div id="toc">
</div>

Here is a list of places we switch modes.

<!--
Example:

    # Parsed in command mode
    echo "hello $name"

    # the RHS of an assignment is parsed as an expression
    var x = 42 + a[i]

    # The arguments inside function calls expressions
    echo $len(s.strip())
-->

## From Command Mode to Expression Mode

### RHS of Assignments

Everything after `=` is parsed in expression mode:

    var x = 42 + f(x)    # RHS of var/setvar
    setvar x += g(y)

    setvar x = obj.method()   

    x = 'myconst'

### `=` and `_` keywords

Likewise, everything after `=` or `_` is in expression mode:

    = 42 + f(x)

Throw away the value:

    _ L.append(x)


### Expression Substitution

    echo $[42 + a[i]]

### Arguments to Inline Function Calls

    echo $strfunc(1, 2, a[i])
    echo @arrayfunc('three', 'four', f(x))

### Parameter Lists

    proc p(x, y) {  # what's between () is in expression mode
      echo $x $y    # back to command mode
    }

### Oil `if`, `while`, and `for`

Expressions appear inside `()`:

    if (x > 0) { 
      echo positive
    }
    
    while (x > 0) {
      setvar x -= 1
    }
    
    for (k, v in mydict) { 
      echo $x $y
    }

## From Expression Mode to Command Mode

### Array Literals

    var myarray = %( /tmp/foo ${var} $(echo hi) @myarray )

### Command Substitution

Everything in between sigil pairs is in command mode:

    var x = $(hostname | tr a-z A-Z) 

    var y = @(seq 3)   # Split command sub

### Block Literals

    var b = &(echo $PWD)

## Examples

### How Are Glob Patterns Written in Each Mode?

No:

    echo '*.py'              # a literal string, not a glob

    echo @glob(*.py)         # syntax error, * is an operator in 
                             # expression mode

    var x = myfunc(*.py)     # ditto, syntax error

Yes:

    echo *.py                # expanded as a glob

    echo @glob('*.py')       # A literal string passed to the builtin
                             # glob function

    var x = f('*.py')        # Just a string

    var x = f(glob('*.py'))  # Now it's expanded

Another way to say this is that Oil works like Python:

```python
from glob import glob
glob('*.py')             # this is a glob
os.listdir('*.py')       # no glob because it's not how listdir() works
```

Also note that Oil has a builtin operator that uses glob aka `fnmatch()`
syntax:

    if (x ~~ '*.py') {  # not yet implemented
      echo 'Python'
    }


