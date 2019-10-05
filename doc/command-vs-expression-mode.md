Could not detect file type from 'command-vs-expression-mode.md'

Here is a list of places we switch modes:

# From Command Mode to Expression Mode

Assignments:

```
var x = 1 + f(x)    # RHS of var/setvar
setvar x = 1 + f(x)
setvar x = obj.method()   

x = 1 + f(x)   # when parse_equals is on, = becomes special
```

`do` parses in expression mode, and throws away the return value:

```
do 1 + f(x)
do obj.method()
```

**Arguments** to Inline function calls:

```
echo $strfunc(x, y + f(z))
echo @arrayfunc(x, y + f(z))
```

**Parameter Lists**

```
func add(x = 5, y = 2) {  # what's between () is in expression mode
  return x + y   # this part is in command mode
}
```

**Oil if/while/for**

```
if (x > 0) { ... }
while (x > 0) { ... }
for (x, y in pairs) { ... }
```


# From Expression Mode to Command Mode

```
var x = func(x) { echo hi; return x +1 }   # everything between {} is in command mode
```


# Other

Braced Vars in Double Quotes:

```
echo ${f(x)}
```

This is an incomplete list.  Double quoted strings are yet another lexer mode I didn't list.


### Does that mean that functions arguments can’t be globs? Eg:

do_something_with_files(data*.dat)?


Good question, yes in expressions globs have to be quoted:

Yes:

```
ls *.py
echo $myfunc('*.py')
if (x ~ '*.py') {  # ~ operator also matches globs, not implemented yet
  echo yes
}

```

No:

```
echo '*.py'  # not a glob
echo $myfunc(*.py)  # syntax error
```

So yeah you do have to have an awareness of what's an expression and what's a "word/command", which is why I highlighted it.
