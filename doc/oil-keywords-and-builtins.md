Oil Keywords and Builtins
=========================



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


