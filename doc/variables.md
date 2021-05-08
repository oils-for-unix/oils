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
of variables follows from that philosophy.  This means that:

- We implement shell-compatible behavior.
- We enhance it with **new features** like expressions over typed data, which
  will be familiar to JavaScript and Python programmers.
- We make the language **stricter**.
  - Procs (shell functions) should be "self-contained", and understandable by
    reading their signature.
  - Remove [dynamic scope]($xref:dynamic-scope).  This mechanism is unfamiliar
    to most programmers, and may result in unintentional variable mutation
    (bugs).
  - Avoid problems with typos by requiring variable **declarations**.
- Even though Oil is stricter, it should still be convenient to use
  interactively.

## Keywords Are More Consistent and Powerful Than Builtins

Oil has 5 keywords affect shell variables.  Unlike shell builtins, they're
statically-parsed, and take dynamically-typed **expressions** on the right.

### Declare With `var` and `const`

This is similar to JavaScript.

    proc p {
      var name = 'Bob'
      const age = 42
      echo "$name is $age years old"
    }

### Mutate With `setvar` and `setglobal`

    proc p {
      var name = 'Bob'       # declare
      setvar name = 'Alice'  # mutate

      setglobal g = 42       # creates or mutates a global variable
    }

### "Return" By Mutating "Out Params" With `setref` (advanced)

    proc p(s, :out) {           # declare out param with :
      setref out = "prefix-$s"  # mutate it to "return" value to caller
    }

This is a more controlled version of shell's dynamic scope.  It reuses the
[nameref]($osh-help) mechanism.

(Implementation detail: it hides the parameter name with a `__` prefix.  This
is due to a perhaps overactive nameref cycle check.)

- *Style guideline*: In some situations, it's better to "return" a value on
  stdout and use `$(myproc)` to retrieve it.

### Comparison to Shell

In contrast, shell and [bash]($xref) have grown many mechanisms for declaring
and mutating variables:

- "bare" assignments like `x=foo`
- **builtins** like `declare`, `local`, and `readonly`
- The `-n` "nameref" flag

Examples:

    readonly name=World        # no spaces allowed around =
    declare foo="Hello $name"
    foo=$((42 + a[2]))
    declare -n ref=foo         # $foo can be written through $ref

## Keywords Behave Differently at the Top Level

Keywords like `var` behave differently in the top-level scope vs. `proc` scope.
This is due to the tension between shell's interactive nature and Oil's
strictness (and to the dynamic nature of the `source` builtin).

The "top-level" of the interpreter is used in two situations:

1. When using Oil **interactively**.
2. As the **global** scope of a batch program.

### Usage Guidelines

Before going into detail, here are some practical guidelines:

- **Interactive** sessions: Use `setvar` only.  This keyword is like Python's
  assignment operator: it creates or mutates a variable.
  - **Short scripts** (~20 lines) can also use this style.
- **Long programs**: Refactor them into composable "functions", i.e. `proc`.
  - First wrap the **whole program** into `proc main(@argv)`.
  - Declare all variables with `var` and `const` declarations.  (This is more like
    JavaScript than Python.)
  - Inside procs, use `setvar` to mutate **local** variables, and `setglobal`
    to mutate **globals**.
  - The **top level** should only have `const` declarations.  (You can use
    `var`, but it has special rules, explained below.)

That's all you need to remember.  The following sections go into more detail.

### The Top-Level Scope Has Only Dynamic Checks

#### Interactive Use: `setvar` only

As mentioned, you only need the `setvar` keyword in an interactive shell:

    oil$ setvar x = 42   # create variable 'x'
    oil$ setvar x = 43   # mutate it

Details:

- `var` behaves like `setvar`: It creates or mutates a variable.  In other
  words, a `var` definition can be **redefined** at the top-level.
- A `const` can also redefine a `var`.
- A `var` can't redefine a `const` because there's a **dynamic** check that
  disallows mutation (like shell's `readonly`).  But there are no *static*
  checks at the top-level.

#### Batch Use: `const` only

It's simpler to use only constants at the top level.

    const USER = 'bob'
    const HOST = 'example.com'

    proc p {
      ssh $USER@$HOST ls -l
    }

This is so you don't have to worry about `var` being redefined by code in
`source mylib.sh`.  A `const` can't be redefined, because it can't be mutated.

Note that putting mutable globals in a dictionary will prevent them from being
redefined:

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
- They don't "silently" mutate variables up the stack, including globals.  That
  is, there's no [dynamic scope]($xref:dynamic-scope) rule.
  - They may take `:out` params instead.

They have **static** checks (parse errors):

- Every variable must be declared once and only once with `var` or `const`.  A
  duplicate declaration is a parse error.
- Mutating a `const` is a parse error.
- `setvar` of an undeclared variable is a parse error.

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

These language constructs all do **assignment** with dynamic scope.  In Oil,
they only mutate the local scope:

- `x=val`
  - And variants `x+=val`, `a[i]=val`, `a[i]+=val`
- `export x=val` and `readonly x=val`
- `${x=default}`
- `mycmd {x}>out`
- `(( x = 42 + y ))`

### Builtins Affected

These builtins are also "isolated" inside procs:

- [read]($osh-help) (`$REPLY`)
- [readarray]($osh-help) aka `mapfile`
- [getopts]($osh-help) (`$OPTIND`, `$OPTARG`, etc.)
- [printf]($osh-help) -v
- [unset]($osh-help) (TODO: fix this)

Oil Builtins:

- [compadjust]($osh-help)
- [run]($oil-help) `--assign-status`

<!-- TODO: should Oil builtins always behave the same way?  Isn't that a little
faster? I think read -line and -all are not consistent.  -->

## More Details

### Syntactic Sugar: Omit `const`

In Oil (but not OSH), you can omit `const` when there's only one variable:

    const x = 'foo'

    x = 'foo'  # Same thing.  This is NOT a mutation as in C or Java.

To prevent confusion, `x=foo` (no spaces) is disallowed in Oil.  Use the `env`
command instead:

    env PYTHONPATH=. ./foo.py  # good
    PYTHONPATH=. ./foo.py`.    # disallowed because it would be confusing

### Examples of Place Mutation

The expression to the left of `=` is called a **place**.  These are basically
Python or JavaScript expressions, except that you add the `setvar` or
`setglobal` keyword.

    setvar x[1] = 2
    setvar d['key'] = 3
    setvar d->key = 3               # syntactic sugar for the above
    setvar func_returning_list()[3] = 3
    setvar x, y = y, x              # swap
    setvar x.foo, x.bar = foo, bar

## Appendices

### Shell Builtins vs. Oil Keywords

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

### Problems With Top-Level Scope In Other Languages

- Julia 1.5 (August 2020): [The return of "soft scope" in the
  REPL"](https://julialang.org/blog/2020/08/julia-1.5-highlights/#the_return_of_soft_scope_in_the_repl).
  - In contrast to Julia, Oil behaves the same in batch mode vs. interactive
    mode, and doens't print warnings.  However, it behaves differently at the
    top level, and we recommend using only `setvar` in interactive shells, and
    only `const` in the global scope of programs.
- Racket: [The Top Level is Hopeless](https://gist.github.com/samth/3083053)
  - From [A Principled Approach to REPL Interpreters](https://2020.splashcon.org/details/splash-2020-Onward-papers/5/A-principled-approach-to-REPL-interpreters)
    (Onward 2020).  Thanks to Michael Greenberg (of Smoosh) for this reference.
  - The unusual behavior of `var` at the top level was partly inspired by this
    paper.  It's also consistent with shell's `declare`!

## Related Documents

- [Oil Keywords](oil-keywords.html)
- [Interpreter State](interpreter-state.html)
  - The shell has a stack of namesapces.
  - Each namespace contains variable name -> cell bindings.
  - Cells have a tagged value (string, array, etc.), and 3 flags (readonly, export, nameref).
- Unpolished details: [variable-scope.html](variable-scope.html)
