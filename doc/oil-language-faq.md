---
default_highlighter: oil-sh
---

Oil Language FAQ
===================

Here are some common questions about the [Oil language]($xref:oil-language).
Many of the answers boil down to the fact that Oil is a **smooth upgrade**
from [bash]($xref).

Old and new constructs exist side-by-side.  New constructs have fewer
"gotchas".

<!-- cmark.py expands this -->
<div id="toc">
</div>

## What's the difference between `$(dirname $x)` and `$len(x)` ?

Superficially, both of these syntaxes take an argument `x` and return a
string.  But they are different:

- `$(dirname $x)` is a shell command substitution that returns a string, and
  **starts another process**.
- `$len(x)` is a function call, and doesn't need to start a process.
  - Note that `len(x)` is an expression that evalutes to an integer, and
    `$len(x)` converts it to a string.

(Note: command subs may be optimized later, as `ksh` does.)

## Why doesn't a raw string work here: `${array[r'\']}` ?

Oil has two array index syntax:

- The **legacy** shell-like syntax `${array[i]}`, which accepts shell
  arithmetic expressions (which consist of number-like strings).
- The [Oil expression subsitution]($oil-help:expr-sub) syntax `$[array[i]]`,
  which accepts Oil expressions (which consist of typed data).

No:

    echo ${array[r'\']}

Yes:

    echo $[array[r'\']]

A similar issue exists with arithmetic.

Old:

    echo $((1 + 2))   # shell arithemtic

New:

    echo $[1 + 2]     # Oil expression

<!--

## Why doesn't the ternary operator work here: `${array[0 if cond else 5]}` ?

The issue is the same as above.  Oil expression are allowed within `$[]` but
not `${}`.

-->

## The `setvar` keyword feels too long.

Yes, but if you upgrade to `bin/oil` instead of `bin/osh`, you can almost
always use `set` (which is an alias for `setlocal`, not `setvar`).

OSH style, works everywhere:

    setvar x = 42

Oil style, which OK for new scripts, may need to change old scripts:

    set x = 42  # nicer, but conflicts with set -o errexit

To avoid the `set` conflict, change this:

    set -o errexit
    set +o errexit

to one of these:

    shopt --set errexit
    shopt --unset errexit

    # same thing
    shopt -s errexit
    shopt -u errexit

