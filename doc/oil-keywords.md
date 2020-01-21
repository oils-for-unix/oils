---
in_progress: yes
---

Oil Keywords
============

<div id="toc">
</div>

## Basics: `const`, `var`, and `setvar`

These will work in OSH or Oil.

### Syntactic Sugar with Oil: `s = 'foo'`

These are the same:

```
const s = 'foo'
s = 'foo'
```

## Advanced: `setref`

To return a value.

```
proc decode (s, :out) {
  setref out = '123'
}
```

## Stricter Style With Oil: `set` and `setglobal`

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


## Assignment Keywords

- dynamic scope vs. local
  - all Oil keywords have local scope


- `setvar` always works.  This is a shell-like, awk-like style.
  - TODO: it should work for setvar i++ and setvar a[key] += weight too
  - local scope only
  - note: you can't mutate a global shadowed by a local this way
  - actually maybe setglobal?  from global scope.  But setvar always works at
    the top level too.
- `var` and `set` are for a stricter style
  - var will error if it's already declared in the scope
  - set will error if it's NOT declared in the scope
- const is like readonly.  Same rules as 'var'.


- special case for `const port = 80`
  - `port = 80`
  - "huffman coding"


TODO: See data-model.md


### Use `var` to initialize variables

Python- or JavaScript- like syntax on RHS.

```
var myint = 1
var mystring = 'str'
var doublequoted = "hello $name"
var myarray = @(ls -a -l)
var mydict = {name: 'bob', age: 10}
var mylist = [42, false, "hello"]
```

### Use `setvar` or `set` to mutate variables

```
setvar myint = 1
```

Spelled with `set`:

```
shopt -s parse-set

set mylist[0] = 43
set mylist[0] += 1  # increment by 1
set mydict['name'] = 'other'
```

In Oil, `set` is a keyword.  To use the `set` builtin, prefix it with `builtin`:

```
builtin set -o errexit
builtin set -- a b c
```

You can also turn on `set` options with the `shopt -o` flag: `shopt -o -s
errexit`.

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

### More

Future work, not implemented:

- `const` (compile-time?)
  - or `let`?
- `auto` for "auto-vivifcation"


## Other Keywords

### `proc` declares a shell-like "function"

### `func` declares a true function

LIke Python or JavaScript.

### `return` is a keyword in Oil

It takes an expression, not a word.  See command vs. expression mode.

### `do`, `pass`, and `pp`

Maybe `=` too.


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
