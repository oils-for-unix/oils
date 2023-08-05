---
in_progress: yes
all_docs_url: -
---

All Docs on Oils
================

The Oils project aims to transform Unix shell into a better programming
language.  It's **our upgrade path from bash**.  It's for Python and JavaScript
programmers who avoid shell.

<div id="toc">
</div>

## Reference (incomplete)

- [Oils Reference](ref/index.html) - These docs underlie `help` builtin, and
  are also published online.
- Links to topics within each chapter:
  - [Index of OSH Topics](osh-help-topics.html)
  - [Index of YSH Topics](ysh-help-topics.html)

## Preliminaries

- [Why Use Oils?](/why.html)  This document is on the home page.
- [INSTALL](INSTALL.html). How do I install Oils?  This text file is also in the
  tarball.
- [A Tour of the Oils Project](project-tour.html).  It's a big project with
  several components to understand!
- [Getting Started](getting-started.html).

## OSH is a Compatible Shell

These docs are for advanced users:

- [Known Differences](known-differences.html) lists differences between OSH and
  other shells.  
- [Quirks](quirks.html) for compatibility.
- [Shell Language Idioms](shell-idioms.html).

## YSH is a New Shell

- [A Tour of YSH](ysh-tour.html).
- [YSH vs. Shell Idioms](idioms.html).  Idioms that are nicer in YSH than shell.
- [What Breaks When You Upgrade to YSH](upgrade-breakage.html).  When you turn
  on YSH, there are some shell constructs you can no longer use.  We try to
  minimize the length of this list.
- [Hay - Custom Languages for Unix Systems](hay.html).  Use Ruby-like
  blocks to declare data and interleaved code.
- [YSH Language FAQ](ysh-faq.html).  Common questions about the
  language.
- [Warts](warts.html).  Mostly for compatibility.

### Language Design

- [A Feel For YSH Syntax](syntax-feelings.html)
- [Language Influences](language-influences.html)
- [Syntactic Concepts](syntactic-concepts.html)
  - [Command vs. Expression Mode](command-vs-expression-mode.html).
- [YSH vs. Shell](oil-vs-shell.html).  How does YSH differ from
  Bourne/POSIX shell?
- [YSH vs. Python](oil-vs-python.html).  How do YSH expressions differ from
  Python?

### The Command Language

**Commands** are made of words, keywords, and other operators.  They're for
I/O, control flow, and abstraction.

- [Command Language](command-language.html): Simple commands, redirects,
  control flow, etc.
- [YSH Keywords](oil-keywords.html). New keywords for assignment, etc.
- Pipeline Idioms.  An essential part of shell that deserves its own document.
- [Procs, Blocks, and Funcs](proc-block-func.html)
- [Modules](modules.html).  Separating programs into files.

### The Word Language

**Words** are expressions for strings, and arrays of strings.

- [Word Language](word-language.html).  Substitution, splicing, globbing, brace
  expansion, etc.
- [Strings: Quotes, Interpolation, Escaping, and Buffers](strings.html)
  - [Unicode](unicode.html).  Oils supports and prefers UTF-8.
- [Special Variables](oil-special-vars.html).  Registers?
- [Simple Word Evaluation](simple-word-eval.html).  Written for shell experts.

### The Expression Language

YSH has typed **expressions**, like Python and JavaScript.

- [Expression Language](expression-language.html).  Types, literals, and
  operators.
- [Egg Expressions](eggex.html).  A new regex syntax, abbreviated *eggex*.

## Languages for Data (Interchange Formats)

YSH supports these languages for data, which are complementary to languages for
code.

- [JSON](json.html): Currently supported only in the Python prototype of YSH.
- [QSN](qsn.html): Quoted String Notation.  A human- and machine-readable
  format for byte strings.
  - [Framing](framing.html)
- [QTT](qtt.html): Quoted, Typed Tables.  An extension of TSV, built on top of
  QSN.

## The Shared Runtime

- [Interpreter State](interpreter-state.html).  What's inside a shell
  interpreter?
  - [Options](options.html).  Parsing and runtime options turn OSH into YSH.
  - [Variable Declaration, Mutation, and Scope](variables.html)
- [Process Model](process-model.html).  The shell language is a thin layer over
  the Unix kernel.
- [Tracing Execution](xtrace.html).  YSH enhances shell's `set -x`.
- Errors
  - [YSH Fixes Shell's Error Handling (`errexit`)](error-handling.html)
  - [Error List](errors.html) 
- [YSH Builtins](oil-builtins.html) (Shell builtins aren't discussed.)
  - [IO Builtins](io-builtins.html)
- [Headless Mode](headless.html).  For alternative UIs on top of YSH.


## For Contributors

- [README.md](README.html).  If you want to modify Oils, start here.  We
  welcome contributions!
- [Doc Toolchain](doc-toolchain.html) and [Doc Plugins](doc-plugins.html).
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)

### Internal Details

- [Notes on Oils Architecture](architecture-notes.html)
  - [Parser Architecture](parser-architecture.html)
