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
  - Note that `len(x)` is an expression that evaluates to an integer, and
    `$len(x)` converts it to a string.

(Note: builtin subs like `${.myproc $x}` are meant to eliminate process
overhead, but they're not yet implemented.)

## How can I return rich values from shell functions / Oil `proc`s?

There are two primary ways:

- Print the "returned" data to `stdout`.  Retrieve it with a command sub like
  `$(myproc)` or a pipeline like `myproc | read --line`.
- Use an "out param" with [setref]($oil-help:setref).

(Oil may grow true functions with the `func` keyword, but it will be built on
top of `proc` and the *builtin sub* mechanism.)

Send us feedback if this doesn't make sense, or if you want a longer
explanation.

## Why doesn't a raw string work here: `${array[r'\']}` ?

This boils down to the difference between OSH and Oil, and not being able to
mix the two.  Though they look similar, `${array[i]}` syntax (with braces) is
fundamentally different than `$[array[i]]` syntax (with brackets).

- OSH supports `${array[i]}`.
  - The index is legacy/deprecated shell arithmetic like `${array[i++]}` or
    `${assoc["$key"]}`.
  - The index **cannot** be a raw string like `r'\'`.
- Oil supports both, but [expression substitution]($oil-help:expr-sub) syntax
  `$[array[i]]` is preferred.
  - It accepts Oil expressions like `$[array[i + 1]` or `$[mydict[key]]`.
  - A raw string like `r'\'` is a valid key, e.g.  `$[mydict[r'\']]`.

Of course, Oil style is preferred when compatibility isn't an issue.

No:

    echo ${array[r'\']}

Yes:

    echo $[array[r'\']]

A similar issue exists with arithmetic.

Old:

    echo $((1 + 2))   # shell arithmetic

New:

    echo $[1 + 2]     # Oil expression

<!--

## Why doesn't the ternary operator work here: `${array[0 if cond else 5]}`?

The issue is the same as above.  Oil expression are allowed within `$[]` but
not `${}`.

-->

## Related

- [Oil Language FAQ]($wiki) on the wiki has more answers.  They may be migrated
  here at some point.

