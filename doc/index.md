Oil Documentation
=================

The Oil project aims to transform Unix shell into a better programming
language.

This manual covers the parts of Oil that are **new and unique**.  In contrast,
the [OSH User Manual](osh-manual.html) describes parts of `osh` that overlap
with other shells like `bash`.

Everything described here is part of the `osh` binary.  In other words, the Oil
language is implemented with a set of backward-compatible extensions, often
using shell options that are toggled with the `shopt` builtin.

(In the distant future, there may be a legacy-free `oil` binary.)

<!-- cmark.py expands this -->
<div id="toc">
</div>

## OSH is a Compatible Shell

- [OSH User Manual](osh-manual.html). How do I use OSH as my shell?
- [Known Differences](known-differences.html) is trivia for advanced users.
  It lists differences between OSH and other shells.
- [errexit](errexit.html) (in progress)

## Oil is a New Shell Language

- [Options](oil-options.html)
- [Keywords and Builtins](oil-keywords-and-builtins.html)
  - [Assignment](oil-assignment.html)
- [Command vs. Expression Mode](command-vs-expression-mode.html)
- [Oil Expressions](oil-expressions.html)
  - [Literal Syntax](oil-literal-syntax.html)
- [Word Language](oil-word-language.html) - Oil extends the "word language".
- [Special Variables](oil-special-vars.html) - Oil extends the "word language".
- [funcs, procs, and blocks](oil-func-proc-block.html)
- [Egg Expressions](eggex.html).  Oil has a new regex syntax called "egg
  expressions", abbreviated *eggexes*.
- [Unicode](unicode.html)

Internal details:

- [Data Model](data-model.html) -- The interpreter
- [Architecture Notes](architecture-notes.html) -- The interpreter
- [Error List](errors.html) 

Other:

- scope
- `evalblock()`

## Other Docs

- [INSTALL](INSTALL.html). How do I install Oil?  This text file is also in the
  tarball.
- [OSH Quick Reference](osh-quick-ref.html), with examples (incomplete).
  This document underlies the `help` builtin, and gives a rough overview of
  what features OSH implements.

Developer Documentation:

- [README.md](README.html).  If you want to modify Oil, start here.  We
  welcome contributions!
- [Github Wiki for oilshell/oil](https://github.com/oilshell/oil/wiki)
