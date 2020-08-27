---
in_progress: yes
---

The Oil Language from 10,000 Feet
=================================

This document describes the Oil language.  It also discusses **future work**.
Related Documents:

- [Oil Language Idioms](idioms.html)
- [Oil Language Design Notes](language-design.html)
- [Why Use Oil?](//www.oilshell.org/why.html)

<div id="toc">
</div> 

## Oil Retains These Shell Concepts

- Commands (pipelines, etc.)
  - `ls -l`
  - `ls -l | wc -l`
- Words
  - double quoted
  - interpolation
- Variables
  - use different assigment builtins
- Shell builtins
  - different ones
- Shell functions, loops, and conditionals
  - different syntax

<!--
Would be nice to show these side-by-side?  Old way and new way.
-->

Oil retains them all.  A big difference is that keywords rather than builtins
are used for assignment.

### Syntactic Concepts

See [Syntactic Concepts in Oil](syntactic-concepts.html)

## The Word Language Is Enhanced


See [Oil Word Language](oil-word-language.html).

- Inline Function Calls

Deferred: Static Printf, Formatters

    echo ${myfloat %.3f}

Formatters (like template languages)

    echo ${myfloat|json}

### Special Variables

[Special Variables](oil-special-vars.html)

- `@ARGV` and `ARGV`


## The Command Language

### New Keywords: `var`, `const`, `setvar`

    var x = 1

auto for autovivification:

    auto dict['key'] += 1

maybe const.  I want that to be compile-time though.

`return` has to be a keyword and not a builtin because it can take arbitrary data types, e.g.

    return {name: 'bob', age: 15}

See [Oil Keywords](oil-keywords.html).

### Shell-Like Builtins

See [Oil Builtins](oil-builtins.html).

- Assignment builtins local, declare, export
- Builtins Accept Long Options
  - TODO: Link HN thread


### Docstrings and Multiline Commands

Note: not implemented.

    ##

    %%%

## The Expression Language is Python-Like

The Expression Language Is Mostly Python

See [Oil Expressions](oil-expressions.html).

- list, dict literals
-  list comprehensions

### Builtin Functions

Python and shell both borrow from C.  Oil borrows from Python and C.

- len()
- min, max
- sorted() ?  Leave this out.

## Runtime Semantics

### Data Structures

- bash-like data structures at first
- fully recursive

Data Types Are Mostly Python?

- "JSON" types in Python: dict, heterogeneous list
- homogeneous string arrays like shell
- homogeneous bool/int/float arrays like R / NumPy

### Process Model

- [Process Model](process-model.html)


### Simple Word Evaluation With shopt -s simple_word_eval 

Mentioned in the last post.  This is big!

### Scope and Namespaces

- Like shell and Python, there is a global scope and function scope..
- shell functions don't live in their own scope?  This is like Lisp-1 vs
  Lisp-2.
- There won't be dynamic scope as in shell.

The `use` builtin will provide scope.

## Deferred Features

- Coprocesses
- Data Frames from R
  - Have to get dict/list/etc. working first
  - date and time types
- Low Level Bindings for POSIX, Linux, Containers 
- Find Dialect
  - replace find
  - need work on this

## Appendix: Why an Upgrade?

Hejlsberg quote?
