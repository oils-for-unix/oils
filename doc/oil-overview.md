---
in_progress: yes
---

The Oil Language from 10,000 Feet
=================================

This document describes the Oil language.  See [What is Oil?](what-is-oil.html)
for the larger context.

It also discusses **future work**.


<div id="toc">
</div> 

## Oil Retains These Shell Concepts

- Commands (pipelines, etc.)
  - `ls -l`
  - `ls -l | wc -l`
- words
  - double quoted
  - interpolation
- variables
  - use different assigment builtins
- shell builtins
  - different ones
- shell functions, loops, and conditionals
  - different syntax

<!--
Would be nice to show these side-by-side?  Old way and new way.
-->

Oil retains them all.  A big difference is that keywords rather than builtins
are used for assignment.

## Syntactic Concepts

### Static Parsing

Like Python, JS.  See Oil language definition.

- [[ ]] and []
- echo -e and $''

- remaining dynamic parsing in shell
  - printf
  - glob
- arithmetic is still somewhat dynamic -- replaced by Oil expressions
- assignment builtins support dynamism, replaced by `var` and `setvar`

### Parse Options to Take Over @, (), {}, `set`, and maybe =

Another concept is parsing modes.


    shopt -s all:oil  # most important thing, turns on many options

    if ( ) {
    }

    echo @array

    set x = 1
    builtin set -o errexit

equals:

    x = 1
    equivalent to 
    const x = 1

This is for Oil as a **configuration language**.

### Command vs. Expression Mode

    echo hi

Expression mode in three places:

    echo @array
    myprog --flag=$f(x, y)
    var z = f(x+1, y)

Control FLow:

   if grep foo
   if (foo) {}   # replaces if [ -n $foo ]; then

   while

   for

   switch/case -- for translation to C++ like mycpp
   match/case


### Sigils, Sigil Pairs, and Lexer Modes

Sigils:

- $foo for string
- @array for array of strings
- : sort of means "code" ?

Sigil Pairs:

- ${x} for word evaluation
- $(( )) for shell arithmetic is deprecated

- $(bare words) for command sub
- @(bare words) for shell arrays
- @[1 2 3] for typed arrays
- @{ } for table literals / embedded TSV

- $// for regexes

- c'' c"" r'' r"" for strings
  - legacy: $'' in command mode

- :{} for blocks
- :() for unevaluated expressions

Table example:

    var people = @{
      name      age:Int
      bob       10_000
      'andy c'  15_000
    }
    var people = {name: @(bob 'andy c'), age: @[10_000 15_000]}


- maybe: #() for tuple?

Sigil pairs often change the lexer mode.


## Syntax

### The Expression Language Is Mostly Python


- list, dict literals
-  list comprehensions


### Word Language: Inline Function Calls, Static Printf, Formatters

    echo ${myfloat %.3f}

Formatters (like template languages)

    echo ${myfloat|json}


### Homogeneous Arrays

- array literals, array comprehensions

### New Keywords: `var`, `set`, `do`, `func`, `return`

    var x = 1

auto for autovivification:

    auto dict['key'] += 1

maybe const.  I want that to be compile-time though.

`return` has to be a keyword and not a builtin because it can take arbitrary data types, e.g.

    return {name: 'bob', age: 15}

### Dict Literals Look like JavaScript

Later: Data Frames.

### String Literals may be r or c

backslashes

### Docstrings and Multiline Commands

    ##

    %%%

## Runtime Semantics

### shopt -s simple-word-eval Does Static Word Evalation

Mentioned in the last post.  This is big!

### Scope and Namespaces

- Like shell and Python, there is a global scope and functino scope..
- shell functions don't live in their own scope?  This is like Lisp-1 vs
  Lisp-2.
- There won't be dynamic scope as in shell.

The `use` builtin will provide scope.

### Functions are like Python/JavaScript

But take simplified keyword args like Julia.

### Data Types Are Mostly Python

- "JSON" types in Python: dict, heterogeneous list
- homogeneous string arrays like shell
- homogeneous bool/int/float arrays like R / NumPy

## Special Variables

`@ARGV` and `ARGV`

## Shell-Like Builtins

Assignment builtins local, declare, export

### Builtins Accept Long Options

TODO: Link HN thread

### Changed: `echo`

- echo simplified
- tweaked: `eval`, `trap`

- `read` will probably be overhauled, simplified
  - don't rely on IFS

### New: `use`, `push`, `repr`

- `use` is like source with namespaces.  I've come up with a good syntax but
  the semantics will be tricky, e.g. caching modules.

- push appends to an array
- repr for debugging
TODO: Probably more for debugging.


## Builtins Can Take Ruby-Like Blocks

NOTE: Haven't decided if blocks have parameters or now?  Maybe just magic
variables.

    cd ~/src { echo $PWD } replaces pushd/popd pairs

Shell options have a stack (modernish also has this):

    shopt -s errexit {
    }

Env is now a builtin and takes a block

    env FOO=bar {
    }

fork builtin replaces the weird `&` terminator:

    { echo 1; sleep 1; echo 2; } &

    fork { echo 1; sleep 1; echo 2 }

wait builtin replaces ( ), because ( ) is going

### `cd`, `env`, and `shopt` Have Their Own Stack

Like Python's context manager.

### `wait` and `fork` builtins Replace () and & Syntax

### `each { }` Runs Processes in Parallel and Replaces `xargs`

each func

each { }

## More Use Cases for Blocks

### Configuration Files

Evaluates to JSON (like YAML and TOML):

    server foo {
      port = 80
    }

And can also be serialized as command line flags.

Replaces anti-patterns:

- Docker has shell
- Ruby DSLs like chef have shell
- similar to HCL I think, and Jsonnet?  But it's IMPERATIVE.  Probably.  It
  might be possible to do dataflow variables... not sure.  Maybe x = 1 is a
  dataflow var?

### Awk Dialect

    BEGIN {
      end
    }

    when x {
    }

### Make Dialect

    rule foo.c : foo.bar {
      cc -o out @srcs
    }

### Flag Parsing to replace getopts

Probably use a block format.  Compare with Python's optparse.o

See issue.

### Unit Tests

Haven't decided on this yet.

    check {
    }

## Builtin Functions From Python, C

Python and shell both borrow from C.  Oil borrows from Python and C.

- min, max
- sorted() ?


## Textual Protocols / Interchange Formats

### JSON

### TSV2

text over binary

- read, echo TSV2 , JSON

## You Can Influence the Design

### How to Give Good Feedback

- make reference to a real shell program
  - show me nice examples
- not just: this is my pet feature that I like.  How does it relate to shell?

### Deferred Features

- Coprocesses
- Data Frames from R
  - Have to get dict/list/etc. working first
  - date and time types
- Low Level Bindings for POSIX, Linux, Containers 
- Find Dialect
  - replace find
  - need work on this
- Regex Dialect
- Bootstrapping: optional static typing
  - Go only bootstrapped after 8 years or so.  Oil might take longer.

- switch/case
- match/case -- algebraic data types, replace case statement?

## Implementation Status

- Nice front end
- But slow.  Really slow interpreter
  - Designing the language with a prototype if you like.

## Appendix: Why an Upgrade?

Hejlsberg quote?


