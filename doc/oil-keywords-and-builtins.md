Oil Keywords and Builtins
=========================

## Keywords

### `var` to declare variables

Python- or JavaScript- like syntax on RHS.

```
var myint = 1
var mystring = 'str'
var doublequoted = "hello $name"
var myarray = @(ls -a -l)
var mydict = {name: 'bob', age: 10}
var mylist = [42, false, "hello"]
```

### `setvar` or `set` to update variables

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

### Future

(Not implemented)

- const (compile-time?)
- auto for "auto-vivifcation"



## Keywords

- var
- set / setvar
- (let ?  const)
- do, pass, and pp
- proc and func
- return

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

## Builtins

- use
- push, repr
- wait, fork

### Enhanced with Block

- cd

(not done)

- wait
- env (not done)
- shopt




Shell-Like Builtins

    Builtins Accept Long Options
    Changed: echo
    New: use, push, repr

Builtins Can Take Ruby-Like Blocks (partially done)

    cd, env, and shopt Have Their Own Stack
    wait and fork builtins Replace () and & Syntax
    each { } Runs Processes in Parallel and Replaces xargs


## Builtins

### cd

It now takes a block:

```
cd ~/src {
  echo $PWD
  ls -l
}

# current directory restored here

echo $PWD
ls -l
```

(This subsumes the functinoality of bash builtins `pushd` and `popd`.)

When a block is passed:

- `cd` doesn't set The `OLDPWD` variable (which is used to implement the `cd -`
  shortcut.)
- The directory stack for `pushd` and `popd` isn't cleared, as it is with a
	normal `cd` command.

### echo

`shopt -s simple_echo` changes the `echo` builtin to accept the following long
flags, as well as the `--` separator between flags and args.

- `-sep`: Characters to separate each argument.  (Default: newline)
- `-end`: Characters to terminate the whole invocation.  (Default: newline)
- `-n`: A synonym for `-end ''`.

### push

Append one or more strings to an array.

```
var array = @(1 '2 two')
push :array three four
echo @array  # prints 4 lines
```

## Builtin Flag Syntax

Oil's builtins accept long flags like `--verbose` and short flags like `-v`.

They behave like the popular GNU utilities on Linux distros, except that
`-long` (single hyphen) means the same thing as `--long`.  It's not a shortcut
for `-l -o -n -g` or `-l=ong`.  (This rule is consistent with the [Go flags
  package][goflags].)

[goflags]: https://golang.org/pkg/flag/

In addition, all of these are equivalent:

- `-sep x`
- `-sep=x`
- `--sep x`
- `--sep=x`

The first is preferred because it's the simplest and shortest.

(Trivia: Oil's flag syntax avoids the issue where `set -oo errexit nounset` is
a confusing equivalent to `set -o errexit -o nounset`.)

### Future

- fork, wait
- log, die
- write
