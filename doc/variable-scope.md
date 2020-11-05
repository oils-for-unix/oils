---
in_progress: yes
default_highlighter: oil-sh
---

Variable Scope in Shell and Oil
===============================

This is for advanced users.  Casual users should can read the first two
sections.

Also see [Oil Keywords](oil-keywords.html).

<div id="toc">
</div>

## Oil Design Goals

This doc is filled with details, so it will help to keep these goals in mind:

- Code written in Oil style (with `proc`) is easier to read/audit than code
  written in shell style.
  - in shell, functions can pollute the caller's stack, because of the dynamic
    scope rule.
- Remove dynamic scope.  This mechanism is unfamiliar to most programmers, and
  may result in mutating variables where you don't expect it.
  - Instead of using dynamic scope by default, Oil lets you choose it
    explicitly, with the `setref` keyword.
- "Subsume" all of shell and bash.  There shouldn't be anything you can do in
  bash that you can't do in Oil.
- But as usual, provide a smooth upgrade path.

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

### Three Keywords

Don't use the old style of `local`, `readonly`, `x=y`.

- Use `const`, `var`, and `setvar`.

This covers 95%+ of shell programming.

### When Dynamic Scope Is Off

`shopt --unset dynamic_scope` 

- it's off when calling a `proc`.
- it's off in  `bin/oil`

This option affects how nearly **every** shell assignment construct behaves.  There are a lot of them!

This option is unset in `bin/oil`, but not `bin/osh`.

That's it!

## More Constructs for Power Users

- Use `setref` for "out params".  TODO: example of out params in C, as an analogy.
- Use `set` and `setglobal` if you want to be stricter.

See [Oil Keywords](oil-keywords.html).


Read on if you want details.

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

The `setlocal` key always does the same thing.  but all these other constructs
**switch** between `setvar` and `setlocal` semantics, depending on `shopt
--unset dynamic_scope`.

- Mutates exactly one scope!

## Where Are These Semantics Used?

### `Dynamic` &rarr; `LocalOrGlobal` (keyword `setvar`)

Shell:

- `x=y`
  - including: `s+=suffix`, `a[i]+=suffix`, `a+=(suffix 2)`.
- `export x=y`
- `readonly x=y`

<!-- note: can all of these be LocalOnly?  It is possible in theory.  -->

New Oil keyword: `setvar`

Constructs That Retrieve Cells:

The other ones deal with values.  These deal with cells.  These also change to
`LocalOrGlobal then.

- `GetCell()` and `GetAllCells()`
  - `declare -p` to print variables
  - `${x@a}` to print flags
  - `pp .cell`

  - weird `TZ` test in `printf`.  I think this could just look in the
    environment itself?  Do `getenv()`?
    - yeah I think this is a separate case
    - I think it should just look for a GLOBAL honestly


### `Dynamic` &rarr; `LocalOnly` (keyword `setlocal`)

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


## Interactive Use

- use `setvar`
- or `set` if you want to define things ahead of time

## Related Links

- [Oil Keywords](oil-keywords.html)
- [Interpreter State](interpreter-state.html)
  - The shell has a stack of namesapces.
  - Each namespace contains variable name -> cell bindings.
  - Cells have 3 flags and a tagged value.


