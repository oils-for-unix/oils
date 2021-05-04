---
in_progress: yes
default_highlighter: oil-sh
---

Variable Scope in Shell and Oil
===============================

NOTE: Most important content has been moved to the [variables](variables.html)
doc.

This doc has **details** for advanced users.

<div id="toc">
</div>

## Design Goals For Scope

- "Subsume" all of shell and bash.  There shouldn't be anything you can do in
  bash that you can't do in Oil.  But as usual, provide a smooth upgrade path.
- Remove dynamic scope.  This mechanism is unfamiliar to most programmers, and
  may result in mutating variables where you don't expect it.
  - Instead of using dynamic scope by default, Oil lets you choose it
    explicitly, with the `setref` keyword.
- Procs should be "self-contained", i.e. understandable by reading their
  signature.

### Dynamic Scope Example

TODO: Improve This Example


    f() {
      out1='y'
      setvar out2 = 'y'
    }

    g() {
      local out1
      local out2

      f
    }

    g  # when it calls f, its variables can be modified

    shopt --unset dynamic_scope
    g  # now they can't be modified; they will be set globally


## What Most Users Need to Know

### When Dynamic Scope Is Off

`shopt --unset dynamic_scope` 

- it's off when calling a `proc`.
- it's off in  `bin/oil`

This option affects how nearly **every** shell assignment construct behaves.  There are a lot of them!

This option is unset in `bin/oil`, but not `bin/osh`.

That's it!

## Three Semantics for Cell Lookup

Cells are locations for variables.

Named after enums.

### `scope_e.Dynamic`

What shell uses

- `setref`: `Dynamic` with `nameref` (no `shopt`)
  - Built on bash's `nameref` feature: `declare -n`.
  - i.e. "Out Params"
  - Does not respect `shopt.

### `scope_e.LocalOrGlobal`

In Oil, it does one of three things:

1. mutates an existing local
2. mutates an existing global
3. create a new global

In shell, it does these things:

2. Mutate any variable of th e name up the stack.

### `scope_e.LocalOnly`

For loop variables, etc.  Mutates exactly one scope!

## Where Are These Semantics Used?

### `LocalOrGlobal` For Reading Variables, and for `setvar`

- reading global vars is normal

Constructs That Retrieve Cells:

The other ones deal with values.  These deal with cells. 

- `GetCell()` and `GetAllCells()`
  - `declare -p` to print variables
  - `${x@a}` to print flags
  - `pp .cell`

  - weird `TZ` test in `printf`.  I think this could just look in the
    environment itself?  Do `getenv()`?
    - yeah I think this is a separate case
    - I think it should just look for a GLOBAL honestly

### `Dynamic` &rarr; `LocalOnly`

Shell:

- Shell Assignment like `x=y`
  - including: `s+=suffix`, `a[i]+=suffix`, `a+=(suffix 2)`.
- Assignment Builtins like
  - `export x=y`
  - `readonly x=y`

These shell constructs mutate.

- osh/word_eval: `${undef=default}` and `${undef:=default}`
- core/process: `myprog {fd}>out.txt`
- osh/sh_expr_eval: `(( i = j ))`, `(( i += j ))`
  - `(( a[i] = j ))`, `(( a[i] += j ))`

### Unchanged: Builtins That Take "Out Params" (keyword `setref`)

These use `setref` semantics.

Idea: You can write functions with out params that also **compose**.  TODO:
Example.

- `read`
- `getopts`
- `mapfile` / `readarray`
- `printf -v`
- `run --assign-status`
- `unset` -- This takes a variable name, so it's like an "out param".

## More Details

### `scope_e.GlobalOnly` and `setglobal`

This one is the easiest to explain, to we leave it for last.

### Other Assignment Constructs

- Shell's `local` is always `LocalOnly`
  - `declare` and `readonly` are also local by default

## Related Links

- [Oil Variables](variables.html)
- [Oil Keywords](oil-keywords.html)
- [Interpreter State](interpreter-state.html)
  - The shell has a stack of namesapces.
  - Each namespace contains variable name -> cell bindings.
  - Cells have 3 flags and a tagged value.

