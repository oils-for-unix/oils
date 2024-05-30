---
in_progress: yes
all_docs_url: ..
body_css_class: width40 help-body
default_highlighter: oils-sh
preserve_anchor_case: yes
---

YSH Command Language Keywords
===

This chapter in the [Oils Reference](index.html) describes new YSH keywords in
the command language.

- Back: [YSH Table of Contents](toc-ysh.html)

<div id="toc">
</div>

## Assignment

### const 

Binds a name to a YSH expression on the right, with a **dynamic** check to
prevent mutation.

    const c = 'mystr'        # equivalent to readonly c=mystr
    const pat = / digit+ /   # an eggex, with no shell equivalent

If you try to re-declare or mutate the name, the shell will fail with a runtime
error.  `const` uses the same mechanism as the `readonly` builtin.

Consts should only appear at the top-level, and can't appear within `proc` or
`func`.

### var

Initializes a name to a YSH expression.

    var s = 'mystr'        # equivalent to declare s=mystr
    var pat = / digit+ /   # an eggex, with no shell equivalent

It's either global or scoped to the current function.

You can bind multiple variables:

    var flag, i = parseArgs(spec, ARGV)

    var x, y = 42, 43

You can omit the right-hand side:

    var x, y  # implicitly initialized to null

### setvar

At the top-level, setvar creates or mutates a variable.

    setvar gFoo = 'mutable'

Inside a func or proc, it mutates a local variable declared with var.

    proc p {
      var x = 42
      setvar x = 43
    }

You can mutate a List location:

    setvar a[42] = 'foo'

Or a Dict location:

    setvar d['key'] = 43
    setvar d.key = 43  # same thing

You can use any of these these augmented assignment operators

    +=   -=   *=   /=   **=   //=   %=
    &=   |=   ^=   <<=   >>=

Examples:

    setvar x += 2  # increment by 2

    setvar a[42] *= 2  # multiply by 2

    setvar d.flags |= 0b0010_000  # set a flag


### setglobal

Creates or mutates a global variable.  Has the same syntax as `setvar`.


## Expression

### equal

The `=` keyword evaluates an expression and shows the result:

    oil$ = 1 + 2*3
    (Int)   7

It's meant to be used interactively.  Think of it as an assignment with no
variable on the left.

### call

The `call` keyword evaluates an expression and throws away the result:

    var x = :| one two |
    call x->append('three')
    call x->append(['typed', 'data'])


## Definitions

### proc

Procs are shell-like functions, but with named parameters, and without dynamic
scope.

Here's a simple proc:

    proc my-cp (src, dest) {
      cp --verbose --verbose $src $dest
    }

Here's the most general form:

    proc p (
      w1, w2, ...rest_words;
      t1, t2, ...rest_typed;
      n1, n2, ...rest_named;
      block) {

      = w1
      = t1
      = n1
      = block
    }

See the [Guide to Procs and Funcs](../proc-func.html) for details.

Compare with [sh-func](chap-builtin-cmd.html#sh-func).

### func

TODO

### ysh-return

To return an expression, wrap it in `()` as usual:

    func inc(x) {
      return (x + 1)
    }

