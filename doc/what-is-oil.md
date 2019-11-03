---
in_progress: yes
---

What is Oil?
============

Oil is an interactive shell and programming language.  It's **our upgrade path
from bash**.

The language is designed to be easier to learn, more consistent, and more
powerful.

It runs existing shell scripts, but also borrows features from Python,
JavaScript, Ruby, and Perl.  It has rich data structures, declarative DSLs, and
reflection/metaprogramming features.

The rest of this doc gives various

<div id="toc">
</div> 

## It Runs Your Existing Shell Scripts

## It's a New Language, which mostly borrows from other languages


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

## High-Level Descriptions

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


## Oil Compared to Other Shells

- link nushell comment from reddit


## Links To Older Descriptions

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

## More Links

- [Why Create a New Unix Shell?](/blog/2018/01/28.html) describes the
  motivation for the Oil project.
- [2019 FAQ](/blog/2018/01/28.html)

