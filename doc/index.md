---
in_progress: yes
all_docs_url: -
---

Oil Documentation
=================

The Oil project aims to transform Unix shell into a better programming
language.  It's **our upgrade path from bash**.  It's for Python and JavaScript
programmers who avoid shell.

<div id="toc">
</div>

## Preliminaries

- [Why Use Oil?](/why.html)  This document is on the home page.
- [INSTALL](INSTALL.html). How do I install Oil?  This text file is also in the
  tarball.
- [A Tour of the Oil Project](project-tour.html).  It's a big project with
  several components to understand!
- [Getting Started](getting-started.html).

## OSH is a Compatible Shell

- [Shell Language Idioms](shell-idioms.html).
- For advanced users
  - [Known Differences](known-differences.html) lists differences between OSH and
    other shells.  
  - [Quirks](quirks.html) for compatibility.

Reference:

- [OSH Help Topics](osh-help-topics.html) (incomplete).  This document
  underlies the `help` builtin.

## Oil is a New Shell Language

- [A Tour of the Oil Language](oil-language-tour.html).
- [Oil vs. Shell Idioms](idioms.html).  Idioms that are nicer in Oil than shell.
- [Shell Language Deprecations](deprecations.html).  When you turn on Oil,
  there are some shell constructs you can no longer use.  We try to minimize
  the length of this list.
- [Oil Language FAQ](oil-language-faq.html).  Common questions about the
  language.
- [Warts](warts.html).  Mostly for compatibility.

Reference:

- [Oil Help Topics](oil-help-topics.html) (incomplete).  This document
  underlies the `help` builtin.

### Notes on Language Design

- [A Feel For Oil's Syntax](syntax-feelings.html)
- [Language Influences](language-influences.html)
- [Syntactic Concepts](syntactic-concepts.html)
  - [Command vs. Expression Mode](command-vs-expression-mode.html).
- [Oil Language vs. Shell](oil-vs-shell.html).  How does Oil differ from
  Bourne/POSIX shell?
- [Oil vs. Python](oil-vs-python.html).  How do Oil's expressions differ from
  Python?

### The Command Language

**Commands** are made of words, keywords, and other operators.  They're for
I/O, control flow, and abstraction.

- [Command Language](command-language.html): Simple commands, redirects,
  control flow, etc.
- [Oil Keywords](oil-keywords.html). New keywords for assignment, etc.
- Pipeline Idioms.  An essential part of shell that deserves its own document.
- [Procs, Blocks, and Funcs](proc-block-func.html)
- [Modules](modules.html).  Separating programs into files.

### The Word Language

**Words** are expressions for strings, and arrays of strings.

- [Word Language](word-language.html).  Substitution, splicing, globbing, brace
  expansion, etc.
- [Strings: Quotes, Interpolation, Escaping, and Buffers](strings.html)
  - [Unicode](unicode.html).  Oil supports and prefers UTF-8.
- [Special Variables](oil-special-vars.html).  Registers?
- [Simple Word Evaluation](simple-word-eval.html).  Written for shell experts.

### The Expression Language

Oil has typed **expressions**, like Python and JavaScript.

- [Expression Language](expression-language.html).  Types, literals, and
  operators.
- [Egg Expressions](eggex.html).  A new regex syntax, abbreviated *eggex*.

## Languages for Data (Interchange Formats)

Oil supports these languages for data, which are complementary to languages for
code.

- [JSON](json.html): Currently supported only in the Python prototype of Oil.
- [QSN](qsn.html): Quoted String Notation.  A human- and machine-readable
  format for byte strings.
  - [Framing](framing.html)
- [QTT](qtt.html): Quoted, Typed Tables.  An extension of TSV, built on top of
  QSN.

## The Shared Runtime

- [Interpreter State](interpreter-state.html).  What's inside a shell
  interpreter?
  - [Options](options.html).  Parsing and runtime options turn OSH into Oil.
  - [Variable Declaration, Mutation, and Scope](variables.html)
- [Process Model](process-model.html).  The shell language is a thin layer over
  the Unix kernel.
- [Tracing Execution](xtrace.html).  Oil enhances shell's `set -x`.
- Errors
  - [Error Handling with `errexit`](errexit.html)
  - [Error List](errors.html) 
- [Oil Builtins](oil-builtins.html) (Shell builtins aren't discussed.)
  - [IO Builtins](io-builtins.html)
- [Headless Mode](headless.html).  For alternative UIs on top of Oil.

## Internal Details

- [Notes on Oil's Architecture](architecture-notes.html)
  - [Parser Architecture](parser-architecture.html)

## For Contributors

- [README.md](README.html).  If you want to modify Oil, start here.  We
  welcome contributions!
- [Toil](toil.html).  Continuous testing on many platforms.
- [Doc Toolchain](doc-toolchain.html) and [Doc Plugins](doc-plugins.html).
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)

<!--

Discarded, maybe delete these

[What is Oil?](what-is-oil.html)  High-level descriptions of the project.

-->
