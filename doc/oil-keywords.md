---
in_progress: yes
default_highlighter: oil-sh
---

Oil Keywords
============

Related:

- [Procs and Blocks](oil-proc-func-block.html)
- [Variables](variables.html)

<div id="toc">
</div>

## Two Styles of Variable Declaration and Assignment

### Legacy Style: `readonly`, `local`, `name=val`

They don't allow expressions on the right.

### Oil's Style: `const`, `var`, `setvar`, `setglobal`, and `setref`

See the doc on [variables](variables.html) for details.

## Expressions Go on the Right

Just like with assignments.

### `=` Pretty Prints an Expression

Useful interactively.

    $ = 'foo'
    (Str)   'foo'
    
    $ = %(one two)
    (StrArray)   ['one', 'two']

### `_` Ignores an Expression

Think of this:

    _ f(x)

as a shortcut for:

    _ = f(x)  # assign to "meh" variable


## Other Kinds of Assignment

### `auto` for Autovivification (future, not implemented)

    auto count += 1

    auto hist['key'] += 1

    auto total += 3.5
    auto hist['key'] += 4.6

## Notes and Examples

### Mutating Arrays

Use `setvar`:

Shell:


    a=(one two three)
    a[0]=zz

Oil:

    var a = %(one two three)
    setvar a[0] = 'zz'  # also acceptable

### Mutating Associative Arrays

Shell:

    declare -A A=(['name']=foo ['type']='dir')
    A['type']=file

Oil:

    var A = {name: 'foo', type: 'dir'}
    setvar A['type'] = 'file'  # also acceptable


## `proc` Disables Dynamic Scope

Recall that [procs](oil-proc-func-block.html) are the way to declare shell-like
functions in Oil.

    proc p {
      echo one
      echo two
    }
    
    p > file.txt

They mostly look like and work like shell functions, but they change scoping rules.

<!--

## Variables and Assignment

TODO: Merge this

I just implemented some more Oil language semantics! [1]

In shell (and Python), there's no difference between variable declaration and
mutation.  These are valid:

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
