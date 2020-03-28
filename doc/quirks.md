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


<!--

### errexit message and optimized subshells

For all shells:

    sh -c 'date'

gets rewritten into:

    sh -c 'exec date'

That is, they **reuse the parent process**.

Most shells don't print any diagnostic info when `errexit` is on.  However, Oil
does:

    osh -o errexit -c 'false'
    [ -c flag ]:1: fatal: Exiting with status 1

`false` is a builtin rather than an external process, so Oil can print that
message.  But when running an external process, the message is lost:

    osh -o errexit -c 'env false'
    (silently fails with code 1)
-->
