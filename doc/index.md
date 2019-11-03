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

- [What is Oil?](what-is-oil.html).  High-level descriptions of the project.
- [The Oil Language From 10,000 Feet](oil-overview.html)  A tour of Oil.
- [INSTALL](INSTALL.html). How do I install Oil?  This text file is also in the
  tarball.
- [OSH Quick Reference](osh-quick-ref.html), with examples (incomplete).  This
  document underlies the `help` builtin, and gives a rough overview of what
  features OSH implements.

## OSH is a Compatible Shell

- [OSH User Manual](osh-manual.html). How do I use OSH as my shell?
- [Known Differences](known-differences.html) is trivia for advanced users.
  It lists differences between OSH and other shells.
- [errexit](errexit.html) (in progress)

## Oil is a New Shell Language

- [Options](oil-options.html)
- [Oil Keywords](oil-keywords.html). (Shell keywords aren't discussed.)
  - [Procs, Funcs, and Blocks](oil-proc-func-block.html)
- [Oil Builtins](oil-builtins.html) (Shell builtins aren't discussed.)
- [Command vs. Expression Mode](command-vs-expression-mode.html) An important
  syntactic concept.  See the [overview](oil-overview) for more syntactic
  concepts.
- [Oil Expressions](oil-expressions.html) The Expression Language is Mostly
  Python.
- [Word Language](oil-word-language.html) - Oil extends the "word language".
- [Special Variables](oil-special-vars.html) - Oil extends the "word language".
- [Egg Expressions](eggex.html).  Oil has a new regex syntax called "egg
  expressions", abbreviated *eggexes*.
- [Unicode](unicode.html)

Internal details:

- [Data Model](data-model.html) -- The interpreter
- [Architecture Notes](architecture-notes.html) -- The interpreter
- [Error List](errors.html) 

Future:

- Scope
- Error Handling
- Builtin Functions: `evalblock()`, etc.
  - TODO: copy from quick ref

## Docs for Contributors

- [README.md](README.html).  If you want to modify Oil, start here.  We
  welcome contributions!
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)
