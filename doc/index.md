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

- [What is Oil?](what-is-oil.html)  High-level descriptions of the project.
- [The Oil Language From 10,000 Feet](oil-overview.html)  A tour of Oil.
- [INSTALL](INSTALL.html). How do I install Oil?  This text file is also in the
  tarball.

<!-- TODO: split up help into 12 docs? -->

## OSH is a Compatible Shell

- [OSH User Manual](osh-manual.html). How do I use OSH as my shell?
- [Known Differences](known-differences.html) is trivia for advanced users.
  It lists differences between OSH and other shells.
- [Quirks](quirks.html)
- [errexit](errexit.html) (in progress)

## Oil is a New Shell Language

- [Options](oil-options.html).  Parsing and runtime options turn OSH into Oil.
- [Oil Keywords](oil-keywords.html). Oil introduces new keywords.  (Shell
  keyword aren't discussed.)
- [Oil Expressions](oil-expressions.html) The Expression Language is Mostly
  Python.
- [Procs, Funcs, and Blocks](oil-proc-func-block.html)
- [Oil Builtins](oil-builtins.html) (Shell builtins aren't discussed.)
- [Word Language](oil-word-language.html) - Oil extends the "word language".
  - [Special Variables](oil-special-vars.html)
  - [Simple Word Evaluation](simple-word-eval.html)
- [Egg Expressions](eggex.html).  Oil has a new regex syntax called "egg
  expressions", abbreviated *eggexes*.

Future:

- Error Handling

## More

These docs span both OSH and Oil.

- [Index of Help Topics](help-index.html) (incomplete).  This document
  underlies the `help` builtin, and gives examples of each Oil feature.  It
  links to sections in the [Help](help.html) page.
- [Command vs. Expression Mode](command-vs-expression-mode.html) An important
  syntactic concept.  See the [overview](oil-overview) for more syntactic
  concepts.
- [Unicode](unicode.html)

Internal Details:

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
