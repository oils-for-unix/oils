---
in_progress: yes
---

Quirks
======

This document describes corner cases in Oil for compatibility.

Related: [Known Differences](known-differences.html).

<div id="toc">
</div>

## For Bash Compatibility

### The meaning of `()` on the RHS

In Oil, **values** are tagged with types like `Str` and `AssocArray`, as
opposed to the *locations* of values (cells).

This statement binds an empty indexed array to the name `x`:

    x=()  # indexed by integers

**Quirk**: When it's clear from the context, `()` means an empty
**associative** array:

    declare -A x=()  # indexed by strings, because of -A

This only applies when the array is empty.  Otherwise the type is determined by
the literal:

    declare x=(one two)  # indexed array
    declare x=(['k']=v)  # associative array

Redundant but OK:

    declare -a x=(one two)  # indexed array
    declare -A x=(['k']=v)  # associative array

Errors:

    declare -A x=(one two)  # inconsistent
    declare -a x=(['k']=v)  # inconsistent


