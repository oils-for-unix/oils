---
in_progress: yes
---

The Oil Language from 10,000 Feet
=================================

Now that I've started implementing the Oil language, I feel more comfortable
writing about it.

I got a few helpful comments on last week's [design notes](22.html), but I'd
like more feedback.  I imagine that new readers might be overwhelmed with
detail, so this post addresses that problem with an overview of what I'm
thinking.

First: what is it?

> Oil is an interactive shell and programming language.  It runs existing shell
> scripts, but also borrows features from Python, JavaScript, Ruby, and Perl.
> For example, it has rich data structures, declarative DSLs, and
> reflection/metaprogramming features.

The larger project is "OSH", but Oil is the "clean slate" version.
Surprisingly few compromises had to be made, as I hope you'll see.

This rest of this post describes roughly what that means.  Keep in mind that
Oil is a large project, and I don't promise to finish any of this!

<div id="toc">
</div> 

## Examples For the Impatient

This post is long, so here are some concrete examples.

An important part of Oil is that existing shell code runs!  These examples from
[Pipelines Support Vectorized, Point-Free, and Imperative
Style][pipelines-post] still run.

[pipelines-post]: ../../2017/01/15.html

--> syntax sh
hist() {
}
f() {
  hist
}
<--

That illustrates some of the good parts of shell.  The bad parts still run as well!

However, Oil is a brand new language.  Due to some tricks I practied while
#[parsing-shell][], like lexer modes, very few compromises had to be made.

- Linux kernel?
- rsync command line?
- Brendan Gregg shell tools?  Show off awk and make?


TODO: function for fib, and then write it to a different directory?
  or maybe look up something in /usr/share/dict/words

  use it as a seven letter scrabble rack?

Fibonacci

    func fib(n) {
      var a = 0
      var b = 1
      for (_ in range(n)) {
        set a, b = b, a+b
      }
      return b
    }

    proc fib {
      var n = $1
      var a = 0
      var b = 1
      for _ in @split($(seq n)) {
        set a, b = b, a+b
      }
      return b
    }

Shell Script

    shopt -s all:oil

    # something with a pipeline
    find . -

    proc main {
    }

## Oil Mostly Borrows From Other Languages

Trying to be conservative.  Not inventing anything new!!!

- Shell for the command syntax.  Piplines, ;, and && ||.

- Python for expression language:
  - [x for x in range(3) if x]

- JavaScript:
  - dict literal -- also probably "object literal"
  - control flow looks like C/JavaScript: if (x) { x } else { x }

- Ruby
  - blocks
- Perl
  - @ sigil, `push` builtin resemblance
  - agglomeration of DSLS: awk/sed.
    - Oil is more like sh/awk/make/regex.  regex is grep/sed.
- Julia
  - also has blocks
  - simplified args and kwargs with `;`

- autovivification from Perl/awk

- Go:
  - builtin flags syntax
  - in-memory utf-8 representation of strings (also Rust and Perl)
    - see FAQ
  - maybe later: `func` type declaration syntax

LATER:

- R language (probably later, need help): data frames, lazy evaluation
- Honorable mention: Lua: reentrant interpreter.  However the use of Unix
  syscalls implies global process state.
- Lisp: symbol types

- Types:
  - MyPy, with Go syntax
  - func add(x Int, y Int) Int { }
  - This probably won't happen for a very long time unless someone helps!
    However I've reserved syntactic room for it.

### Differences from Python

- no operator overloading
- no "accidentally quadratic

## High-Level Descriptions

### Paradigms and Style

- shell is already mix of: 
  - dataflow: concurrent processes and files, pipelines
    - instead of Clojure's "functions and data", we have "processes and files".
      Simple.  Functional.  Transforming file system trees is a big part of containers.

  - imperative: the original Bourne shell added this.  
    - "functions" are really procedures; return
    - iteration constructs: while / for / break / continue
    - conditional constructs: if / case

Oil:

  - getting rid of: ksh.  Bourne shell is good; ksh is bad because it adds bad
    string operators.
    - ${x%%a}  ${x//}  getting rid of all this crap.  Just use functions.
    - korn shell arrays suck.  Replaced with python-like arrays
    - historical note: usenix 93.   korn shell was  used for GUIs and such!

- Add Python STRUCTURED DATA.
  - the problem with PROCESSES AND FILES is that it forces serialization everywhere.
  - Structured Data in Oil

-  Add **declarative** paradigm to shell.
  - Package managers like Alpine Linux, Gentoo need declarative formats.  So do
    tools like Docker and Chef.

- Language-Oriented -- internal DSLs.

### What Should It Be Used For?

- System Administration / Distributed Systems / Cloud / Containers
  - particularly gluging together build systems and package managers in
    different languages.  It's a "meta" tool.
- Scientific Computing / Data Science / "Data Engineering"  -- gluing things
  together that weren't meant to be glued together

### Links To Older Descriptions

- The [design notes in the last post](22.html), in particular the array
  rewrites on Zulip.
- Posts tagged #[oil-language][]
  - Particularly two posts on [Translating Shell to Oil][osh-to-oil].  (As
    noted in the last post, the project is no longer focuse don translation.)
  - arrays I did sigils
- [2019 FAQ][faq-what-happened]
- Implementing the Oil Expression language (wkki)
- why-a-new-shell ?

[faq-what-happened]: ../06/17.html#toc_5

==> md-blog-tag oil-language
==> md-blog-tag osh-to-oil


Zulip: Oil as a clean slate ?


## `bin/oil` is `bin/osh` with the option group `all:oil`

Everything described here is part of the `osh` binary.  In other words, the Oil
language is implemented with a set of backward-compatible extensions, often
using shell options that are toggled with the `shopt` builtin.

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


