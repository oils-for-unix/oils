---
default_highlighter: oils-sh
---

OSH Quirks
==========

This document describes corner cases in OSH.

Related: [Known Differences](known-differences.html).

<div id="toc">
</div>

## For Bash Compatibility

### The meaning of `()` on the RHS

In Oils, **values** are tagged with types like `Str` and `AssocArray`, as
opposed to the *locations* of values (cells).  The construct `()` on the RHS
generates an instance of a distinct type `InitializerList`, which modifies the
content of the LHS that it is assigned to.

This statement binds an empty indexed array to the name `x`:

    x=()  # indexed by integers

This clears the content of the associative array.

    declare -A x=()  # indexed by strings, because of -A

These assign elements.

    declare -a x=(one two)  # set elements
    declare -a x=(['k']=v)  # set an element to the index $((k))
    declare -A x=(['k']=v)  # set an element to the key 'k'

This is not supported:

    declare -A x=(key value)  # Error in osh

When the variable does not exist and a type is not specified, the assignment
creates an indexed array and applies the `InitializerList` to the created
array.

    declare x=(one two)  # creates an indexed array
    declare x=(['k']=v)  # creates an indexed array

**Quirk (osh <= 0.27.0)**: The construct `()` had an ambiguous type, which was
either `BashArray` or `BashAssoc` depending on its content and the context.
When it's clear from the context, `()` meant an empty **associative** array:

    declare -A x=()  # indexed by strings, because of -A

This was only applied when the array is empty.  Otherwise the type was
determined by the literal:

    declare x=(one two)  # indexed array
    declare x=(['k']=v)  # associative array

These were redundant but OK:

    declare -a x=(one two)  # indexed array
    declare -A x=(['k']=v)  # associative array

These produced errors:

    declare -A x=(one two)  # inconsistent
    declare -a x=(['k']=v)  # inconsistent

## Interactive Shell

### With job control, the DEBUG trap is disabled for the last part of a pipeline

First, some background.  These two shell features are fundamentally
incompatible:

- Job control: e.g. putting a pipeline in a process group, so it can be
  suspended and cancelled all at once.
- `shopt -s lastpipe` semantics: the last part of a pipeline can (sometimes) be
  run in the current shell.
  - [OSH]($xref) uses it by default because it makes `echo hi | read myvar` work.  So
    [OSH]($xref) is like [zsh]($xref), but unlike [bash](xref).

As evidence of this incompatibility, note that:

- [bash]($xref) simply ignores the `shopt -s lastpipe` setting in job control
  shells
- [zsh]($xref) doesn't allow you to suspend some pipelines

---

Now that we have that background, note that there's is a **third** feature that
interacts: the `DEBUG` trap.

[OSH]($xref) emulates the [bash]($xref) `DEBUG` trap, which runs before "leaf"
commands like `echo hi`, `a=b`, etc.

If we run this trap before the last part of a pipeline, **and** that part is
run in the current shell (`lastpipe`), then the DEBUG trap makes an existing
race condition worse.

For example, in

    echo hi | cat

there's nothing stopping `echo hi` from finishing before `cat` is even started,
which means that `cat` can't join the process group of the leader.

So we simply disable the `DEBUG` trap for the last part of the pipeline, but
**only** when job control is enabled.  This won't affect debugging batch
programs.

Related issues in other shells:

- bash: <https://superuser.com/questions/1084406/chained-pipes-in-bash-throws-operation-not-permitted>
- fish: <https://github.com/fish-shell/fish-shell/issues/7474>

<!--

### errexit message and optimized subshells

For all shells:

    sh -c 'date'

gets rewritten into:

    sh -c 'exec date'

That is, they **reuse the parent process**.

Most shells don't print any diagnostic info when `errexit` is on.  However, YSH
does:

    osh -o errexit -c 'false'
    [ -c flag ]:1: fatal: Exiting with status 1

`false` is a builtin rather than an external process, so YSH can print that
message.  But when running an external process, the message is lost:

    osh -o errexit -c 'env false'
    (silently fails with code 1)
-->

## Related 

- The doc on [warts](warts.html) relates to YSH.

