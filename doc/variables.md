---
in_progress: yes
default_highlighter: oil-sh
---

Variable Declaration, Mutation, and Scope
=========================================

This document describes the semantics of variables in Oil and distills them to
practical usage guidelines.

<div id="toc">
</div>

## Oil Design Goals

The Oil language is a graceful upgrade to shell, and the behavior of variables
is no exception.  This means that:

- We implement shell-compatible behavior, enhance it, and make it stricter.
- We add features that will be familiar to JavaScript and Python programmers.
  In particular, Oil has **typed data** and variable **declarations**.
- Even though Oil is stricter, it should still be convenient to use
  interactively.

## Keywords Are More Consistent and Powerful Than Builtins

Oil has 5 **keywords** affect shell variables.

### Declare With `var` and `const`

This is similar to JavaScript.

    proc p {
      var name = 'Bob'
      const age = 42
      echo "$name is $age years old"
    }

### Mutate With `setvar` and `setglobal`

    proc p {
      var name = 'Bob'
      setvar name = 'Alice'

      setglobal g = 42  # creates or mutates a global variable
    }

### "Return" By Mutating "Out Params" With `setref` (advanced)

TODO: It does NOT use dynamic scope.  Instead it uses `scope_e.Parent`

But it uses the "nameref" mechanism.  (Implementation detail: it hides the
param name with a `__` prefix.  This is due to a perhaps overactive nameref
cycle check, and could go away.)

Keywords are statically-parsed, and take dynamically-typed **expressions** on
the right.  Example:

    const  name = 'World'              # quotes required
    var    foo  = "Hello $name"
    setvar foo  = 42 + a[2] + f(x, y)  # arbitrary expressions

### Comparison to Shell

In contrast, shell and [bash]($xref) have grown many mechanisms for declaring
and mutating variables:

- **builtins** like `declare`, `local`, and `readonly`
- "bare" assignments like `x=foo`
- The `-n` "nameref" flag

Example:

    readonly name=World        # no spaces allowed around =
    declare foo="Hello $name"
    foo=$((42 + a[2]))

## Keywords Behave Differently at the Top Level

Keywords like `var` behave differently in the top-level scope vs. `proc` scope.
This is due to the tension between shell's interactive nature and Oil's
strictness.

### Usage Guidelines

Before going into detail, here are some practical guidelines:

- When using Oil interactively, use `setvar` only.  Like Python's assignment
  operator, it creates or mutates a variable.
  - Short scripts (~20 lines) can also use this style.
- Refactor long scripts into composable "functions", i.e. `proc`.  First wrap
  the whole program into `proc main(@argv)`, and declare all variables.
  - The `proc` may have `var` and `const` declarations.  (This is more like
    JavaScript than Python.)
  - The top level should only have `const` declarations.  (You can use `var`,
    but it has special rules, explained below.)
  - Use `setvar` to **mutate local** variables, and `setglobal` to mutate
    **globals**.

That's all you need to remember.  The following sections go into more detail.

### The Top-Level Scope Has Only Dynamic Checks

The "top-level" of the interpreter is used in two situations:

- When using Oil **interactively**.
- As the **global** scope of a batch program.

("Top-level" means you're not inside a shell function or `proc`.)

#### Interactive Use: `setvar` only

As mentioned, you only need the `setvar` keyword in an interactive shell:

    oil$ setvar x = 42
    oil$ setvar x = 43

We encourage this style because `var` and `const` behave **differently** at the
top level than they do in functions.  This is related to the dynamic nature of
the `source` builtin, and the resulting inability to statically check
definitions.

Details:

- `var` behaves like `setvar`.  In contrast to `proc` scope, a `var` definition
  can be redefined at the top-level.
- `const` does a *dynamic* check, like shell's `readonly`).  There's no
  *static* check as in `proc`.  As above, and in contrast to `proc` scope, a
  `const` can redefine a `var`.

#### Batch Use: `const` only

It's simpler to use only constants at the top level.

    const USER = 'bob'
    const HOST = 'example.com'

    proc p {
      ssh $USER@$HOST ls -l
    }

This is so you don't have to worry about `var` being redefined by `source`.  In
contrast, a `const` can't be redefined because it can't be mutated.

Putting mutable globals in a dictionary will prevent them from being redefined:

    const G = {
      mystate = 0
    }

    proc p {
      setglobal G->mystate = 1
    }

### `proc` Scope Has Static Checks

Procs are Oil's stricter notion of "shell functions".  They are self-contained
and composable:

- They take named parameters
  - And check that there aren't too few or too many arguments
- They don't "silently" mutate variables up the stack, or mutate globals (no
  dynamic scope)
  - They may take `:out` params instead

#### Declare with `const` and `var`

- `const` declares a local or global constant (like `readonly`)
- `var` declares a local or global variable (like `local` or `declare`)

#### Mutate with `setvar` and `setglobal`

- `setvar` mutates a local
- `setvar` mutates a global

Expressions like these should all work.  They're basically identical to Python,
except that you use the `setvar` or `setglobal` keyword to change locations.

    setvar x[1] = 2
    setvar d['key'] = 3
    setvar func_returning_list()[3] = 3
    setvar x, y = y, x  # swap
    setvar x.foo, x.bar = foo, bar

## Procs Don't Use "Dynamic Scope"

Bourne shell uses a rule called "dynamic scope" for variable name lookup.  It
means that a function can **read and mutate** the locals of its caller, its
caller's caller, and so forth.

Example:

    g() {
      echo "f_var is $f_var"  # g can see f's local variables
    }

    f() {
      local f_var=42
      g
    }

    f

Oil code should use `proc` instead.  Inside a proc call, the `dynamic_scope`
option is implicitly disabled (equivalent to `shopt --unset dynamic_scope`).

This means that adding the `proc` keyword to the definition of `g` changes its
behavior:

    proc g() {
      echo "f_var is $f_var"  # Undefined!
    }

### Shell Language Constructs Affected

- TODO

### Builtins Affected

- Shell Assignment
  - TODO: grep for SetLocalShopt
- Builtins
  - read
  - getopts
  - printf -v
  - TODO: whatever SetRef() and SetRefString() become

<!--
Note: this can sorta produce a leak?  If you GUESS the name of a caller's
variable, you can pass it to its grandchild and mutate it?

I think this is necessary for composability.
-->

## Details

### Syntactic Sugar: Omit `const`

In Oil (but not OSH), you can omit `const` when there's only one variable:

    const x = 'foo'

    x = 'foo'  # same thing

The second statement is **not** a mutation!  Also note that `x=foo` (no spaces)
is disallowed in Oil to avoid confusion.

You can use `env PYTHONPATH=. ./foo.py` in place of `PYTHONPATH=. ./foo.py`.

## Appendices

### Shell Builtins vs. Oil Keywords

This section may help experienced shell users understand Oil.

Shell:

    g=G                       # global variable
    readonly c=C              # global constant

    myfunc() {
      local x=X               # local variable
      readonly y=Y            # local constant

      x=mutated               # mutate local
      g=mutated               # mutate global
      newglobal=G             # create new global

      caller_var=mutated      # dynamic scope (Oil doesn't have this)
    }

Oil:

    var g = 'G'               # global variable
    const c = 'C'             # global constant

    proc myproc {
      var x = 'L'             # local variable
      const y = 'Y'           # local constant

      setvar x = 'mutated'    # mutate local
      setvar g = 'mutated'    # mutate global
      setvar newglobal = 'G'  # create new global

                              # For dynamic scope, Oil uses setref and an
                              # explicit ref param.  See below.
    }

- `var` declares a new variable in the current scope (global or local)
- `const` is like `var`, except the binding can never be changed
- `setvar x = 'y'` is like `x=y` in shell (except that it doesn't obey [dynamic
  scope]($xref:dynamic-scope).)
  - If a local `x` exists, it mutates it.
  - Otherwise it creates a new global `x`.
  - If you want stricter behavior, use `set` rather than `setvar`.

----


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

### Problems With Top-Level Scope In Other Languages

- Racket: See Principled Approach to REPL's
  -  Thanks to Michael Greenberg (of Smoosh) for this reference
- Julia 1.5, Scope, and REPLs
  - Oil doesn't print and warnings.  It just behaves differently, and we give a
    style guideline to only use `const` at the top level to avoid a potential
    issue with `source`.

## Related Documents

- Unpolished Details: [variable-scope.html](variable-scope.html)

