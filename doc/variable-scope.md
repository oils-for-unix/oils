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

## Details

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

## Related Links

- [Oil Variables](variables.html)
