---
in_progress: yes
all_docs_url: -
---

Oil Documentation
=================

The Oil project aims to transform Unix shell into a better programming
language.  It's **our upgrade path from bash**.

<!-- cmark.py expands this -->
<div id="toc">
</div>

## Preliminaries

- [Why Use Oil?](/why.html)  This document is on the home page.
- [INSTALL](INSTALL.html). How do I install Oil?  This text file is also in the
  tarball.

<!-- TODO: split up help into 12 docs? -->

## OSH is a Compatible Shell

- [OSH User Manual](osh-manual.html). How do I use OSH as my shell?
- [Known Differences](known-differences.html) is trivia for advanced users.
  It lists differences between OSH and other shells.
- [Quirks](quirks.html) for compatibility.
- [errexit](errexit.html) (in progress)

## Oil is a New Shell Language

- [The Oil Language From 10,000 Feet](oil-overview.html)  A tour of Oil.
- [Oil Language Idioms](idioms.html).  A list of idioms you may want to use.
- [Shell Language Deprecations](deprecations.html).  When you turn on Oil,
  there are some shell constructs you can no longer use.  We try to minimize
  the length of this list.
- [Syntactic Concepts](syntactic-concepts.html)
  - [Command vs. Expression Mode](command-vs-expression-mode.html).

The shell **command** language has been enhanced:

- [Procs, Funcs, and Blocks](oil-proc-func-block.html)
- [Oil Keywords](oil-keywords.html). New keywords for assignment, etc.
- [Oil Builtins](oil-builtins.html) (Shell builtins aren't discussed.)
  - [IO Builtins](io-builtins.html)

Commands are made of **words**:

- [Word Language](oil-word-language.html).  Oil extends the "word language".
- [Special Variables](oil-special-vars.html)
- [Simple Word Evaluation](simple-word-eval.html).  Written for shell experts.

Oil has a new **expression** language:

- [Oil Expressions](oil-expressions.html) are similar to Python and JavaScript.
- [Egg Expressions](eggex.html).  A new regex syntax, abbreviated *eggex*.

More:

- [Options](oil-options.html).  Parsing and runtime options turn OSH into Oil.
- [Oil Language Design Notes](language-design.html)
- Future: Error Handling

## Interchange Formats

- [JSON](json.html): Currently supported only in the Python prototype of Oil.
- [QSN](qsn.html): Quoted String Notation.  A human- and machine-readable
  format for byte strings.
- [QTSV](qtsv.html): An extension of TSV, built on top of QSN.
- [Unicode](unicode.html).  Oil supports and prefers UTF-8.

## Online Help

[Index of Help Topics](help-index.html) (incomplete).  This document underlies
the `help` builtin, and gives examples of each Oil feature.  It links to
sections in the [Help](help.html) page.

## Internal Details

- [Interpreter State](interpreter-state.html)
- [Process Model](process-model.html).  Shell is a language that lets you use
  low-level Unix constructs.
- [Notes on Oil's Architecture](architecture-notes.html)
  - [Parser Architecture](parser-architecture.html)
- [Error List](errors.html) 
- [Toil](toil.html).  Continuous Testing on Many Platforms.

## For Contributors

- [README.md](README.html).  If you want to modify Oil, start here.  We
  welcome contributions!
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)

<!--

Discarded, maybe delete these

[What is Oil?](what-is-oil.html)  High-level descriptions of the project.

-->
