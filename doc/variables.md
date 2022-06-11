---
default_highlighter: oil-sh
---

Variable Declaration, Mutation, and Scope
=========================================

This doc addresses these questions:

- How do variables behave in Oil?
- What are some practical guidelines for using them?

<div id="toc">
</div>

## Oil Design Goals

The Oil language is a graceful upgrade to shell, and the behavior
of variables follows from that philosophy.

- Oil implements shell-compatible behavior.
- It enhances shell with **new features** like expressions over typed data, which
  will be familiar to Python and JavaScript programmers.
- It's a **stricter** language.
  - Procs (shell functions) are self-contained and modular.  In other words,
    they're understandable by reading their signature.
  - We removed [dynamic scope]($xref:dynamic-scope).  This mechanism isn't
    familiar to most programmers, and may cause accidental mutation (bugs).
  - Oil has variable **declarations** like JavaScript, which can prevent
    trivial bugs.
- Even though Oil is stricter, it should still be convenient to use
  interactively.

## Keywords Are More Consistent and Powerful Than Builtins

Oil has 5 keywords affect shell variables.  Unlike shell builtins, they're
statically-parsed, and take dynamically-typed **expressions** on the right.

### Declare With `var` and `const`

This is similar to JavaScript.

    proc p {
      var name = 'Bob'
      const age = (20 + 1) * 2
      echo "$name is $age years old"  # Bob is 42 years old
    }

### Mutate With `setvar` and `setglobal`

    proc p {
      var name = 'Bob'       # declare
      setvar name = 'Alice'  # mutate

      setglobal g = 42       # create or mutate a global variable
    }

### "Return" By Mutating Out Params With `setref` (advanced)

"Out Params" are a more controlled version of shell's dynamic scope.  They
reuse the [nameref]($osh-help) mechanism.

    proc p(s, :myout) {           # declare out param with :
      setref myout = "prefix-$s"  # mutate it to "return" value to caller
    }

- *Style guideline*: In some situations, it's better to "return" a value on
  stdout, and use `$(myproc)` to retrieve it.
- *Implementation detail*: The out parameter name is "hidden" with a `__`
  prefix.  This avoids a problem with nameref cycle detection.

### Comparison to Shell

Shell and [bash]($xref) have grown many mechanisms for "declaring" and mutating
variables:

- "bare" assignments like `x=foo`
- **builtins** like `declare`, `local`, and `readonly`
- The `-n` "nameref" flag

Examples:

    readonly name=World        # no spaces allowed around =
    declare foo="Hello $name"
    foo=$((42 + a[2]))
    declare -n ref=foo         # $foo can be written through $ref

These constructs are all discouraged in Oil code.

## Keywords Behave Differently at the Top Level (Like JavaScript)

The "top-level" of the interpreter is used in two situations:

1. When using Oil **interactively**.
2. As the **global** scope of a batch program.

Experienced Oil users should know that keywords like `var` behave differently
in the top-level scope vs. `proc` scope.  This is due to the tension between
shell's interactive nature and Oil's strictness (and to the dynamic nature of
the `source` builtin).

For reference, JavaScript's modern `let` keyword has similar behavior.

### Usage Guidelines

Before going into detail on keyword behavior, here are some practical
guidelines:

- **Interactive** sessions: Use `setvar` only.  This keyword is like Python's
  assignment operator: it creates or mutates a variable.
  - **Short scripts** (~20 lines) can also use this style.
- **Long programs**: Refactor them into composable "functions", i.e. `proc`.
  - First wrap the **whole program** into `proc main(@argv)`.
  - Declare all variables with `var` and `const`.
  - Inside procs, use `setvar` to mutate **local** variables, and `setglobal`
    to mutate **globals**.
  - The top level should only have `const` declarations.  (You can use `var`,
    but it has special rules, explained below.)

That's all you need to remember.  The following sections explain the rationale
for these guidelines.

### The Top-Level Scope Has Only Dynamic Checks

The lack of static checks affects the recommended usage for both interactive
sessions and batch scripts.

#### Interactive Use: `setvar` only

As mentioned, you only need the `setvar` keyword in an interactive shell:

    oil$ setvar x = 42   # create variable 'x'
    oil$ setvar x = 43   # mutate it

Details on top-level behavior:

- `var` behaves like `setvar`: It creates or mutates a variable.  In other
  words, a `var` definition can be **redefined** at the top-level.
- A `const` can also redefine a `var`.
- A `var` can't redefine a `const` because there's a **dynamic** check that
  disallows mutation (like shell's `readonly`).

#### Batch Use: `const` only

It's simpler to use only constants at the top level.

    const USER = 'bob'
    const HOST = 'example.com'

    proc p {
      ssh $USER@$HOST ls -l
    }

This is so you don't have to worry about a `var` being redefined by a statement
like `source mylib.sh`.  A `const` can't be redefined because it can't be
mutated.

It may be useful to put mutable globals in a constant dictionary, as it will
prevent them from being redefined:

    const G = {
      mystate = 0
    }

    proc p {
      setglobal G->mystate = 1
    }

### `proc` Scope Has Static Checks

Procs are Oil's stricter notion of "shell functions", and they have additional
**static checks** (parse errors):

- Every variable must be declared once and only once with `var` or `const`.  A
  duplicate declaration is a parse error.
- Mutating a `const` is a parse error.
- `setvar` of an undeclared variable is a parse error.

## Procs Don't Use "Dynamic Scope"

Procs are designed to be encapsulated and composable like processes.  But the
[dynamic scope]($xref:dynamic-scope) rule that Bourne shell functions use
breaks encapsulation.
  
Dynamic scope means that a function can **read and mutate** the locals of its
caller, its caller's caller, and so forth.  Example:

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

### Reading Variables

This means that adding the `proc` keyword to the definition of `g` changes its
behavior:

    proc g() {
      echo "f_var is $f_var"  # Undefined!
    }

This affects all kinds of variable references:

    proc p {
      echo $foo         # look up foo in command mode
      var y = foo + 42  # look up foo in expression mode
    }

As in Python and JavaScript, a local `foo` can *shadow* a global `foo`.  Using
`CAPS` for globals is a common style that avoids confusion.  Remember that
globals should usually be constants in Oil.

### Shell Language Constructs That Write Variables

In shell, these language constructs assign to variables using dynamic
scope.  In Oil, they only mutate the **local** scope:

- `x=val`
  - And variants `x+=val`, `a[i]=val`, `a[i]+=val`
- `export x=val` and `readonly x=val`
- `${x=default}`
- `mycmd {x}>out` (stores a file descriptor in `$x`)
- `(( x = 42 + y ))`

### Builtins That Write Variables

These builtins are also "isolated" inside procs, using local scope:

- [read]($osh-help) (`$REPLY`)
- [readarray]($osh-help) aka `mapfile`
- [getopts]($osh-help) (`$OPTIND`, `$OPTARG`, etc.)
- [printf]($osh-help) -v
- [unset]($osh-help)

Oil Builtins:

- [compadjust]($osh-help)
- [run]($oil-help) `--assign-status`

<!-- TODO: should Oil builtins always behave the same way?  Isn't that a little
faster? I think read --line and --all are not consistent.  -->

### Reminder: Proc Scope is Flat

All local variables in shell functions and procs live in the same scope.  This
includes variables declared in conditional blocks (`if` and `case`) and loops
(`for` and `while`).

    proc p {  
      for i in 1 2 3 {
        echo $i
      }
      echo $i  # i is still 3
    }

It also includes Oil's first-class blocks:

    var x = 42
    cd /tmp {
      var x = 0  # ERROR: x is already declared
    }

## More Details

### Examples of Place Mutation

The expression to the left of `=` is called a **place**.  These are basically
Python or JavaScript expressions, except that you add the `setvar` or
`setglobal` keyword.

    setvar x[1] = 2                 # array element
    setvar d['key'] = 3             # dict element
    setvar d->key = 3               # syntactic sugar for the above
    setvar x, y = y, x              # swap

<!--
Note: these may be valid in Tea, but not Oil

    setvar func_returning_list()[3] = 3
    setvar x.foo, x.bar = foo, bar
-->

### Bare Assignment

`shopt --set parse_equals` is currently **off** in both OSH and Oil.  It allows
constants to be declared without the `const` keyword:

    const x = 'foo'

    x = 'foo'  # Similar.  This is NOT a mutation as in C or Java.

However, it doesn't do a static check for *'const' already defined in proc*.
It will be used for future config-like use cases:

    subdomain app.example.com {  # subdomain proc takes a string and block
      root = '/home/www/bin/'    # no var or const keyword necessary
    }

    subdomain docs.example.com {
      root = '/home/www/docs/'   # not a redefinition
                                 # blocks may or may not introduce a new scope
    }

When it's enabled, `x=foo` (no spaces) is disallowed to prevent confusion.  Use
the `env` command instead:

    env PYTHONPATH=. ./foo.py  # good
    PYTHONPATH=. ./foo.py`.    # disallowed because it would be confusing

### Temp Bindings

Temp bindings precede a simple command:

    PYTHONPATH=. mycmd

They create a new namespace on the stack where each cell has the `export` flag
set (`declare -x`).

In Oil, the lack of dynamic scope means that they can't be read inside a
`proc`.  So they're only useful for setting environment variables, and can be
replaced with:

    env PYTHONPATH=. mycmd
    env PYTHONPATH=. $0 myproc  # using the ARGV dispatch pattern

## Appendix A: More on Shell vs. Oil

This section may help experienced shell users understand Oil.

Shell:

    g=G                        # global variable
    readonly c=C               # global constant

    myfunc() {
      local x=X                # local variable
      readonly y=Y             # local constant

      x=mutated                # mutate local
      g=mutated                # mutate global
      newglobal=G              # create new global

      caller_var=mutated       # dynamic scope (Oil doesn't have this)
    }

Oil:

    var g = 'G'                # global variable (discouraged)
    const c = 'C'              # global constant

    proc myproc {
      var x = 'L'              # local variable
      const y = 'Y'            # local constant

      setvar x = 'mutated'     # mutate local
      setglobal g = 'mutated'  # mutate global
      setvar newglobal = 'G'   # create new global

                               # There's no dynamic scope, but you can use
                               # "out params" with setref.

    }

## Appendix B: Problems With Top-Level Scope In Other Languages

- Julia 1.5 (August 2020): [The return of "soft scope" in the
  REPL](https://julialang.org/blog/2020/08/julia-1.5-highlights/#the_return_of_soft_scope_in_the_repl).
  - In contrast to Julia, Oil behaves the same in batch mode vs. interactive
    mode, and doesn't print warnings.  However, it behaves differently at the
    top level.  For this reason, we recommend using only `setvar` in
    interactive shells, and only `const` in the global scope of programs.
- Racket: [The Top Level is Hopeless](https://gist.github.com/samth/3083053)
  - From [A Principled Approach to REPL Interpreters](https://2020.splashcon.org/details/splash-2020-Onward-papers/5/A-principled-approach-to-REPL-interpreters)
    (Onward 2020).  Thanks to Michael Greenberg (of Smoosh) for this reference.
  - The behavior of `var` at the top level was partly inspired by this
    paper.  It's consistent with bash's `declare`, and similar to JavaScript's
    `let`.

## Related Documents

- [Oil Keywords](oil-keywords.html)
- [Interpreter State](interpreter-state.html)
  - The shell has a stack of namespaces.
  - Each namespace contains {variable name -> cell} bindings.
  - Cells have a tagged value (string, array, etc.) and 3 flags (readonly,
    export, nameref).
- Unpolished details: [variable-scope.html](variable-scope.html) and
  [proc-block-func.html](oil-proc-block-func.html)

