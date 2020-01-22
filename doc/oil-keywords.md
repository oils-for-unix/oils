---
in_progress: yes
---

Oil Keywords
============

<div id="toc">
</div>

## Two Styles for Declaration and Assignment

### `const`, `var`, and `setvar` are shell-like and interactive

Shell:

```
readonly c=C

myfunc() {
  local x=L
  x=mutated

  newglobal=G
}
```

OSH:

```
const c = 'C'

proc myproc {
  var x = 'L'
  setvar x = 'mutated'

  setvar newglobal = 'G'
}
```

- `var` declares a new variable in the current scope (global or local)
- `const` is like `var`, except the binding can never be changed
- `setvar x = 'y'` is like `x=y` in shell (except that it doesn't obey [dynamic
  scope]($xref:dynamic-scope).)
  - If a local `x` exists, it mutates it.
  - Otherwise it creates a new global `x`.
  - If you want stricter behavior, use `set` rather than `setvar`.

### `var` and `set`/`setglobal` are Oil-like and stricter

- `set` mutates a local that's been declared
- `setglobal` mutates a global that's been decalred
- `c = 'X'` is syntactic sugar for `const c = 'X'`.  This is to make it more
  compact, i.e. for "Huffman coding" of programs.

```
c = 'X'  # syntactic sugar for const c = 'X'

proc myproc {
  var x = 'L'
  set x = 'mutated' 

  set notglobal = 'G'   # ERROR: neither a local or global
}
```

It's rarely necessary to mutate globals in shell scripts, but if you do, use
the `setglobal` keyword:

```
var g = 'G'
proc myproc {
  setglobal g = 'mutated'

  setglobal notglobal = 'G'  # ERROR: not a global
}
```

## Other Kinds of Assignment

### Mutating Arrays

You can use `setvar` or `set`:

Shell:

```
a=(one two three)
a[0]=zz
```

Oil:

```
var a = @(one two three)
set a[0] = 'zz'

setvar a[0] = 'zz'  # also acceptable
```

### Mutating Associative Arrays

Shell:

```
declare -A A=(['name']=foo ['type']='dir')
A['type']=file
```

Oil:

```
var A = {name: 'foo', type: 'dir'}
set A['type'] = 'file'

setvar A['type'] = 'file'  # also acceptable
```


### Advanced: `setref` is for "out parameters"

To return a value.  Like "named references" in [bash]($xref:bash).

```
proc decode (s, :out) {
  setref out = '123'
}
```

### `=` pretty prints an expression

Useful interactively.

```sh-prompt
$ = 'foo'
(Str)   'foo'

$ = @(one two)
(StrArray)   ['one', 'two']
```

<!--

LATER: If we ever get true integers and floats!

## Autovivification with `setvar`

Or honestly this could be auto?

auto count += 1
auto hist['key'] += 1


proc main { 
  setvar count += 1   # it's now 1

  hist = {}
  setvar hist['key'] += 1

  setvar hist['key'] += weight  # later: floating point
}

-->


<!--

### Declaration / Assignment

### Mutation

Expressions like these should all work.  They're basically identical to Python,
except that you use the `setvar` or `set` keyword to change locations.

There implementation is still pretty hacky, but it's good to settle on syntax and semantics.

```
set x[1] = 2
set d['key'] = 3
set func_returning_list()[3] = 3
set x, y = y, x  # swap
set x.foo, x.bar = foo, bar
```

https://github.com/oilshell/oil/commit/64e1e9c91c541e495fee4a39e5a23bc775ae3104

-->


<!--

Future work, not implemented:

- `auto` for "auto-vivifcation"

when we get integers.

-->


## Defining "Functions"

### `proc` declares a shell-like "function"

```
proc p {
  echo one
  echo two
}

p > file.txt
```

<!--
### `func` declares a true function

LIke Python or JavaScript.

-->

### `return` is a keyword in Oil

It takes an expression, not a word.  See command vs. expression mode.

```
proc p {
  var status = '1'

  echo 'hello'

  return status  # not $status
}

p
echo $?  # prints 1
```

(This is intended to be consistent with a future `func`.)



<!--
### `do` and `pass`


- `pass` evaluates an expression and throws away its result.   It's intended to be used for left-to-right function calls.  See the `sub()` example in this thread:

https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/left-to-right.20syntax.20ideas

- `pp` pretty prints an expression.

They both have to be **keywords** because they take an expression, not a bunch of words.

-----

Unfortunately I found that `do/done` in shell prevents us from adding `do`:

    do f(x)   #can't write this
    pass f(x)   # it has to be this, which doesn't read as nicely :-(


Not sure what to do about it... we can add a mode for `oil:all` to repurpose `do`, but I'm not sure it's worth it.  It's more complexity. 

So basically **every** call that doesn't use its result has to be preceded with
`pass` now:

    pass f(x)
    pass obj.method()
    var y = f(x)
    var z = obj.method()

Kind of ugly ... :neutral:


https://github.com/oilshell/oil/commit/dc7a0474b006287f2152b54f78d56df8c3d13281

-->


<!--

## Variables and Assignment

TODO: Merge this


I just implemented some more Oil language semantics! [1]

In shell (and Python), there's no difference between variable declaration and mutation.  These are valid:

```
declare x=1  
declare x=2  # mutates x, "declare" is something of a misnomer
x=2  # better way of mutating x
f() {
    local y=1
      local y=2  # mutates y
        y=2  # better way of mutating y
}
```

Likewise, `z=3` can be any of these 3, depending on the context:

1. mutating a local
2. mutating a global
3. creating a new global

In Oil, there are separate keywords for declaring variables and mutating them.

```
var x = 1
var x = 2  # error: it's already declared

setvar x = 2  # successful mutation
set x = 2  # I plan to add shopt -s parse-set to take over the 'set' builtin, which can be replaced with `shopt` or `builtin set`
```

(Ever notice that the set and unset builtins aren't opposites in shell ?!?!)

You can mutate a global from a function:

```
var myglobal = 'g'
f() {
    set myglobal = 'new'
      set other = 'foo'  # error: not declared yet!
}
```

Comments appreciated!

[1] https://github.com/oilshell/oil/commit/54754f3e8298bc3c272416eb0fc96946c8fa0694


I just implemented `shopt -s parse_set`:

https://github.com/oilshell/oil/commit/277c3525aacad48947124c70a52176f5ee447bc5

Note that `shopt -s all:oil` turns on all the `parse_*` options.

So now you can do:

```
var x = 1
set x = 2
setvar x = 3  # don't need this long way
```

To use the `set` builtin, prefix it with `builtin`

```
builtin set -o errexit
builtin set -- a b c
```

Most programs shouldn't need to use the `set` builtin in Oil.  Of course, `shopt -u parse_set` unsets it if desired.

Comments welcome!

-->
