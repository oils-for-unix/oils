---
default_highlighter: oil-sh
in_progress: true
---

A Tour of the Oil Language
==========================

This doc describes the Oil language from a "clean slate" perspective.
It doesn't assume you know how to program in shell, although shell users will
see similarities and simplifications.

Rememnber, Oil is for Python and JavaScript programmers who avoid shell!  See
the [project FAQ](//www.oilshell.org/blog/2021/01/why-a-new-shell.html) for
more background.

TODO:

- Oil Language Influences

<div id="toc">
</div>

## Preliminaries

You start Oil just like you'd start bash, fish, or Python:

<!-- oil-sh below skips code block extraction, since it doesn't run -->

```none
bash$ oil                # assuming it's installed

oil$ echo 'hello world'  # command typed into Oil
hello world
```

In the sections below, we'll save space by showing output in comments:

    echo 'hello world'       # prints 'hello world'

## Examples

### Hello World

Of course, you can also type the commands into a file `hello.oil`.  This is a
complete Oil program, which is identical to a shell program:

    echo 'hello world'     # prints 'hello world'

But Oil has `const` and `var` keywords:

    const name = 'world'
    echo "hello $name"     # prints 'hello world'

With rich Python-like expressions on the right:

    var x = 42             # an integer, not a string
    setvar x = min(x, 0)   # mutate a var with setvar

    setvar x += 5          # Increment by 5
    echo $x                # prints '5'

### Complex Example

## Feelings, Concepts, Sublanguages

- A Feel for Oil's Syntax.
- Syntactic Concepts: command vs. expressions
- Sublanguages (lexer modes)

Example: pipe character

- string language: usually literal
- word language: no meaning, syntax error (e.g. in for loop)
  - or `${x|html}` ?  That is another mini-language.
- command language: pipelines
- expression language: means |

Sublanguages:

- string, word, command, expression
  - var sub is a minor language?  But | means something

## The Command Sublanguage

### Simple Commands

Commands are just space-separated list of "words", which are usually unquoted:

    ls -l /tmp   # Runs the external 'ls' command

    echo 'hi'    # Run the shell builtin 'echo' (quoting for clarity)

<!-- leaving off: aliases -->

### Redirects

    echo hi > tmp.txt  # write to a file
    sort < tmp.txt

Multiline strings are a replacement for shell here docs:

    sort <<< '''
    one 
    two
    three
    '''

---

Pipelines, conditionals, and loops are all compound command (as opposed to the
simple ones above).

Note that Oil code uses shell's `||` and `&&` in very limited circumstances,
since `errexit` is on by default.

### Variable Declaration and Mutation

### Pipelines

Pipelines are a powerful method manipulating text:

    ls | wc -l                       # count files in this directory
    find /bin -type f | xargs wc -l  # in this subtree

TODO: You can also use JSON, CSV/TSV, HTML, etc.

### Conditionals

If statements, with `elif` and `else:

    if test --file foo {
      echo 'foo is a file'
    } elif test --dir foo {
      echo 'foo is a directory'
    } else {
      echo 'neither'
    }

With expressions

    if (x > 0) {
      echo "$x is positive"
    }

Case:

    case $x {
      (*.py)
        echo 'Python'
        ;;
      (*.sh)
        echo 'Shell'
        ;;
    }

(You can also use the shell style of `if foo; then then` and `case $x in`, but
this is discouraged.)

### Loops

    for x in one two *.py {
      echo $x
    }  # prints 'one', 'two', 'foo.py', 'bar.py'


Command:

   while test -n $foo {
     read $foo
   }

Expression:

    var x = 0
    while (x > 0) {
      echo "x = $x"
      # TODO: implement this
      #setvar x -= 1
    }

### Procs (Shell Functions) and Ruby-like Blocks

Define units of reusable code with the `proc` keyword, and invoke them just
like any other command:

    proc mycopy(src, dest) {
      cp --verbose $src $dest
    }

    touch log.txt
    # mycopy is a proc, so shells don't run an external command
    mycopy log.txt /tmp  # runs cp --verbose

Some builtins take blocks directly:

    cd /tmp {
      echo *.py
      echo $PWD  # /tmp
    }
    echo $PWD    # back to original direcory

    # TODO: fix crash
    #shopt --unset errexit {
    #  mycopy x y  # ignore errors
    #  mycopy y z  # ignore errors
    #}

## String Literals

Strings appear in words, but also in expressions.

### Single- and Double-Quoted

### C-style, Multiline

- Double quoted: They can have substitutions with ${} $[] etc.

## The Word Sublanguage

### Substitution and Splicing

- variable sub - `$var`
  - what about `${var:-default}` and so forth?
- command sub - `$(hostname)`
- expression sub - `$[1 + 2 * 3]`
- TODO: builtin sub

### Inline Function Calls

- splicing `@myarray`
- inline function calls like `@split(x)` and `$join()`

### Brace Expansion

This prints andy@example.com and bob@example.com:

    write {andy,bob}@example.com   

### Globs

    # If nothing matches, evaluates to empty list
    echo *.py    

## Python-like Expressions

TODO: link docs

### Literals (numbers, lists, dicts, etc.)

These are the same:

    var x = %(one two three)
    var y = ['one', 'two', 'three']

### Operators

    var x = 42 + 1
    var y = $'foo\n' ++ "hello $name"

### Egg Expressions (Oil Regexes)

These are real expressions!

## Builtins

### Proc-Like (Shell Builtins)

These are simple commands, but they almost form their own language.

- `source`
  - `module`
- `eval`

### Functions

   var x = split('foo bar')   
   write @x

### An Example Module

    #!/usr/bin/env oil

    module main || return 0
    #source $_this_dir/lib/util.oil

    proc myproc {
      echo hi
    }

    #runproc @ARGV

## The Runtime

### Shell Options with `shopt`

### shvars

- `IFS`
- `_ESCAPE`
- `_DIALECT`

### Registers

- `$?` and `_status`
- `_buffer`
- `_this_dir`

## Features Not Shown

- exotic stuff like process sub
- rarely used shell stuff like `until`
- legacy shell stuff: `[[`, `$(( ))`, etc.

## Summary

Oil is a clean language!  With these concepts

- String Literals
- Words (substitution, splicing, globs, and brace expansion)
- Commands
- Expressions

## Related Docs

Contrast:

- [Oil Language Idioms](idioms.html) - Oil side-by-side with shell.
- *A Tour of the Oil project*. TODO: Describe Oil, OSH, oven, the shell runtime,
  headless shell, etc.

## Appendix: Outline

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

