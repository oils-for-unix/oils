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


## Preliminaries

- [INSTALL](INSTALL.html). How do I install Oils?  This text file is also in the
  tarball.
- [A Tour of the Oils Project](project-tour.html).  It's a big project with
  several components to understand!
- [Getting Started](getting-started.html).  How do I use the shell?
- [FAQ on Documentation](faq-doc.html).  Where do I find docs?

## Reference

Like many other docs, this is still in progress:

- [Oils Reference](ref/index.html) - These docs underlie `help` builtin, and
  are also published online.
- Links to topics within each chapter:
  - [Index of OSH Topics](ref/index-osh.html)
  - [Index of YSH Topics](ref/index-ysh.html)

## Interactive Shell

- [Headless Mode](headless.html).  For alternative UIs on top of YSH.
- [Completion](completion.html) (doc in progress).  We emulate bash completion.

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
- [YSH Language FAQ](ysh-faq.html).  Common questions about the
  language.

### Design Concepts, Comparisons

- [A Feel For YSH Syntax](syntax-feelings.html)
- [Language Influences](language-influences.html)
- [Syntactic Concepts](syntactic-concepts.html)
  - [Command vs. Expression Mode](command-vs-expression-mode.html).
- [YSH vs. Shell](oil-vs-shell.html).  How does YSH differ from
  Bourne/POSIX shell?
- [YSH vs. Python](oil-vs-python.html).  How do YSH expressions differ from
  Python?
- [Warts](warts.html).  Mostly for compatibility.

YSH has 3 main sublanguages:

- **Command** language, which now consistently uses `{ }` for blocks.
  - [Hay - Custom Languages for Unix Systems](hay.html).  Use Ruby-like
    blocks to declare data and interleaved code.
- **Word** language.
  - [Simple Word Evaluation](simple-word-eval.html).  Written for shell
    experts.
- **Expression** language on typed data.
  - [Egg Expressions](eggex.html).  A new regex syntax, abbreviated *eggex*.

Crosscutting issues:

- [Variable Declaration, Mutation, and Scope](variables.html)
- [Strings: Quotes, Interpolation, Escaping, and Buffers](strings.html)
  - [Unicode](unicode.html).  Oils supports and prefers UTF-8.
- [YSH Builtins](oil-builtins.html) (Shell builtins aren't discussed.)
  - [IO Builtins](io-builtins.html)

## Data Languages Avoid Ad-Hoc Parsing

YSH supports these languages for data, which are complementary to languages for
code.

- [JSON](json.html): Currently supported only in the Python prototype of YSH.
- [QSN](qsn.html): Quoted String Notation.  A human- and machine-readable
  format for byte strings.
  - [Framing](framing.html)
- [QTT](qtt.html): Quoted, Typed Tables.  An extension of TSV, built on top of
  QSN.

## The Shared Oils Runtime

- [YSH Fixes Shell's Error Handling (`errexit`)](error-handling.html)
- [Tracing Execution](xtrace.html).  YSH enhances shell's `set -x`.
- [Options](options.html).  Parsing and runtime options turn OSH into YSH.

Internal details:

- [Interpreter State](interpreter-state.html).  What's inside a shell
  interpreter?
- [Process Model](process-model.html).  The shell language is a thin layer over
  the Unix kernel.

## For Contributors

- [README.md](README.html).  If you want to modify Oils, start here.  We
  welcome contributions!
- [Doc Toolchain](doc-toolchain.html) and [Doc Plugins](doc-plugins.html).
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)
- [Old Docs](old/index.html).  Drafts that may never be completed.

Internal Architecture:

- [Notes on Oils Architecture](architecture-notes.html)
  - [Parser Architecture](parser-architecture.html)

<!-- vim: set sw=2: -->
