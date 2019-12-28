---
in_progress: yes
---

Command vs. Expression Mode
===========================

- command mode: `unquoted` is a string, while `$dollar` is a variable.
- expression mode: `'quoted'` is a string, while `unquoted` is a variable.


<div id="toc">
</div>


Here is a list of places we switch modes:

## From Command Mode to Expression Mode

Assignments:

```oil
var x = 1 + f(x)    # RHS of var/setvar
setvar x = 1 + f(x)
setvar x = obj.method()   

x = 1 + f(x)   # when parse_equals is on, = becomes special
```

`do` parses in expression mode, and throws away the return value:

```oil
do 1 + f(x)
do obj.method()
```

**Arguments** to Inline function calls:

```
echo $strfunc(x, y + f(z))
echo @arrayfunc(x, y + f(z))
```

**Parameter Lists**

```oil
func add(x = 5, y = 2) {  # what's between () is in expression mode
  return x + y   # this part is in command mode
}
```

**Oil if/while/for**

```oil
if (x > 0) { ... }
while (x > 0) { ... }
for (x, y in pairs) { ... }
```


## From Expression Mode to Command Mode

```oil
var x = func(x) { echo hi; return x +1 }   # everything between {} is in command mode
```


## Other

Braced Vars in Double Quotes:

```oil
echo ${f(x)}
```

This is an incomplete list.  Double quoted strings are yet another lexer mode I didn't list.


## Does that mean that functions arguments can’t be globs?

For example:

```oil
do_something_with_files(data*.dat)?
```


Good question, yes in expressions globs have to be quoted:

Yes:

```oil
ls *.py
echo $myfunc('*.py')
if (x ~ '*.py') {  # ~ operator also matches globs, not implemented yet
  echo yes
}

```

No:

```oil
echo '*.py'  # not a glob
echo $myfunc(*.py)  # syntax error
```

So yeah you do have to have an awareness of what's an expression and what's a "word/command", which is why I highlighted it.




Right I should have clarified – they don’t turn globbing back on. It’s just a string. It’s up to the function that is called to interpret as a glob or not.

It’s exactly like the difference between:

```python
from glob import glob; glob('*.py')  # yes glob
os.listdir('*.py')  # no glob because it's not how listdir() works
```

in Python. Single quoted strings in Oil are just like string literals in Python. Does that make sense?

I’m not sure what you mean by myEcho? Both of these work in Oil just like they
do in sh:

```sh
echo *
echo '*'
```

Because you’ve never entered expression mode. You’re still in command mode.

