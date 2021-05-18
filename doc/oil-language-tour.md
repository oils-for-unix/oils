---
default_highlighter: oil-sh
in_progress: true
---

A Tour of the Oil Language
==========================

This is a clean slate description!  I don't make too much reference to shell,
although shell users will see the similarities and simplifications.

Remember Oil is meant to be familiar to Python and JS programmers.

Contrast:

- idioms doc
- tour of the Oil project

<div id="toc">
</div>

## Hello World

Here is a complete Oil program, which is identical to a shell program:

    echo 'hello world'     # prints 'hello world'

Constants and double quoted strings:

    const name = 'world'
    echo "hello $name"     # ditto, prints 'hello world'

Python-like expressions:

    var x = 42             # an integer, not a string
    setvar x = min(x, 0)   # mutate with setvar, accepts Python-like expressions
    setvar x += 5          # Incremenet
    echo $x                # prints '5'

Shell-like pipelines:

    ls | wc -l             # count files int his directory

## Command Language

### Simple Commands (Three Types)

Builtins

    echo 'hi'

External

    ls -l

"Functions" with the `proc` keyword:

   proc mycopy(src, dest) {
     cp --verbose $src $dest
   }

   mycopy log.txt /tmp

<!-- leaving off: aliases -->

## Outline

OK, I guess `.md` is OK but there is the problem that the code snippets have to be tested.  I think that the tour should quickly go over everything that's idiomatic:

- command language
  - simple commands
    - builtins
    - external commands
    -  Ruby-like blocks -- e.g. `cd /tmp { pwd }`.  This still needs more implementation.
  - redirects
  - pipelines
  - control flow
    - if
    - case
    - for
    - while
  - procs
  - variable declaration and mutation
  - blocks
    - cd, shopt
    - maybe: fork and wait
- word language
  - variable sub - `$var`
  - command sub - `$(hostname)`
  - expression sub - `$[1 + 2 * 3]`
  - TODO: builtin sub
  - splicing `@myarray`
  - inline function calls like `@split(x)` and `$join()`
- expression language
  - this is mostly Python
  - eggex

It can have a lot of links to other docs.  It's possible that this doc could get really long so we should find ways to keep it short and sweet.

## Left Out

- exotic stuff like process sub
- rarely used shell stuff like `until`
- legacy shell stuff: `[[`, `$(( ))`, etc.

## More Info

