---
in_progress: yes
default_highlighter: oils-sh
---

OSH Standard Library - Tiny Code, Evolved Over Years
===========

The [OSH][] standard library runs under both OSH and bash.  ([YSH][] has a
separate standard library.)

This doc briefly describes a few hundred lines of code, documented in the Oils
reference:

- [Oils Reference](ref/) > [OSH Table of Contents](ref/toc-osh.html)


[OSH]: $xref
[YSH]: $xref


<div id="toc">
</div> 

## Intro

I use shell as a quick / iterative / incremental development environment.

I use "task files" and write down everything I do, so I don't forget them.

They evolve and grew over time, but are still small.

### Example of Task File

    : ${LIB_OSH=stdlib/osh}  # to share with bash
    source $LIB_OSH/bash-strict.sh
    source $LIB_OSH/task-five.sh

    test-foo() {
      echo hi
    }

    task-five "$@"


## List of Libraries

### two

Trivial functions I use all the time.

### bash-strict

Catch errors.

Saves you some boilerplate.

### no-quotes

Test framework without extra levels of quoting.  Compare to git sharness.

    nq-capture
    nq-capture-2
    nq-assert

### byo-server

- Test discovery
- Probably:
  - task discovery 
  - auto-completion

May want to fold this into task-five.

### task-five

- Task files

## Appendix

### Why no standard way to set `$REPO_ROOT`?

We commonly use this idiom:

    REPO_ROOT=$(cd $(dirname $0)/..; pwd)

But there is no library for it, because there's no standard way for it.  Other
variants I've seen:

    pwd -P          # we use pwd 
    readlink -f $0  

That is, there's not one way to do it when symlinks are involved.

Most of our scripts must be run from repo root, and there are no symlinks to
them.

(Note that in OSH or YSH you can use `$_this_dir` instead of `$REPO_ROOT`, but
it's not available in bash.)

