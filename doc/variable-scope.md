---
in_progress: yes
default_highlighter: oil-sh
---

Variable Scope in Shell and Oil
===============================

Also see [Oil Keywords](oil-keywords.html).

<div id="toc">
</div>

## `setvar` vs. `setref` Semantics

- `setvar` respects `shopt --unset dynamic_scope`.
- `setref` doesn't.

### Example

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


## Where They Are Used

### `setref` is for "Out Params"

- `read`
- `getopts`
- `mapfile` / `readarray`
- `printf -v`
- `run --assign-status`

### `setvar` is for Variables Specified "Statically"

- Shell's `x=y` and Oil's `setvar x = 'y'`
- `s+=suffix`, `a[i]+=suffix`, a+=(suffix 2)
- `(( i = j ))`, `(( i += j ))`
- `(( a[i] = j ))`, `(( a[i] += j ))`
- `${undef=default}` and `${undef:=default}
- `myprog {fd}>out.txt`
- `export`

### Constructs That Use Neither

- `local` is neither obviously
  - `declare` and `readonly` are also local
- Oil's `set` / `setlocal` / `setglobal`
